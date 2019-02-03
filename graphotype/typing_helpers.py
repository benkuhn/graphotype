"""
typing_helpers: Modified code from typing.py for better compatibility.

We provide:
- python version-independent `eval_type(t, ns)`
- python version-independent `get_type_hints(o, ns=None)` which always resolves
  forward references properly (never returns ForwardRef or raw strings).

We decided that 'locals' and 'globals' are confusing and don't need to be
exposed in the interface. We will always evaluate types with an empty locals
dict.

"""

import sys

import typing_inspect

# These imports work for 3.7:
import types
from types import WrapperDescriptorType, MethodWrapperType, MethodDescriptorType
from typing import Optional, TypeVar


_allowed_types = (types.FunctionType, types.BuiltinFunctionType,
                  types.MethodType, types.ModuleType,
                  WrapperDescriptorType, MethodWrapperType, MethodDescriptorType)


# Hacked version of python3.7's typing.get_type_hints.
def get_type_hints(obj, ns=None):
    """Return type hints for an object.

    This is often the same as obj.__annotations__, but it handles
    forward references encoded as string literals, and if necessary
    adds Optional[t] if a default value equal to None is set.

    The argument may be a module, class, method, or function. The annotations
    are returned as a dictionary. For classes, annotations include also
    inherited members.

    TypeError is raised if the argument is not of a type that can contain
    annotations, and an empty dictionary is returned if no annotations are
    present.

    BEWARE -- the behavior of globalns and localns is counterintuitive
    (unless you are familiar with how eval() and exec() work).  The
    search order is locals first, then globals.

    - If no dict arguments are passed, an attempt is made to use the
      globals from obj (or the respective module's globals for classes),
      and these are also used as the locals.  If the object does not appear
      to have globals, an empty dictionary is used.

    - If one dict argument is passed, it is used for both globals and
      locals.

    - If two dict arguments are passed, they specify globals and
      locals, respectively.
    """

    if getattr(obj, '__no_type_check__', None):
        return {}
    # Classes require a special treatment.
    if isinstance(obj, type):
        hints = {}
        for base in reversed(obj.__mro__):
            if ns is None:
                base_globals = sys.modules[base.__module__].__dict__
            else:
                base_globals = ns
            ann = base.__dict__.get('__annotations__', {})
            for name, value in ann.items():
                if value is None:
                    value = type(None)
                if isinstance(value, str):
                    value = ForwardRef(value, is_argument=False)
                value = eval_type(value, base_globals)
                hints[name] = value
        return hints

    if ns is None:
        if isinstance(obj, types.ModuleType):
            ns = obj.__dict__
        else:
            ns = getattr(obj, '__globals__', {})
    hints = getattr(obj, '__annotations__', None)
    if hints is None:
        # Return empty annotations for something that _could_ have them.
        if isinstance(obj, _allowed_types):
            return {}
        else:
            raise TypeError('{!r} is not a module, class, method, '
                            'or function.'.format(obj))
    defaults = _get_defaults(obj)
    hints = dict(hints)
    for name, value in hints.items():
        if value is None:
            value = type(None)
        if isinstance(value, str):
            value = ForwardRef(value)
        value = eval_type(value, ns)
        if name in defaults and defaults[name] is None:
            value = Optional[value]
        hints[name] = value
    return hints


# Hacked version of python3.7.2's typing.eval_type.
def eval_type(t, ns):
    """Recursively evaluate all forward references in the given type t using the given namespace."""

    while is_forward_ref(t):
        t = t._evaluate(ns, None)

    args = typing_inspect.get_args(t, evaluate=True)
    if args:
        ev_args = tuple(eval_type(a, ns) for a in args)
        if ev_args == args:
            return t

        # FIXME(lincoln): This depends on typing internals, specifically the
        # _GenericAlias impl, but I don't know any other way.
        res = t.copy_with(ev_args)
        res._special = t._special
        return res

    return t


# Copy of python3.7.2's typing._get_defaults. Currently no changes to it.
def _get_defaults(func):
    """Internal helper to extract the default arguments, by name."""
    try:
        code = func.__code__
    except AttributeError:
        # Some built-in functions don't have __code__, __defaults__, etc.
        return {}
    pos_count = code.co_argcount
    arg_names = code.co_varnames
    arg_names = arg_names[:pos_count]
    defaults = func.__defaults__ or ()
    kwdefaults = func.__kwdefaults__
    res = dict(kwdefaults) if kwdefaults else {}
    pos_offset = pos_count - len(defaults)
    for name, value in zip(arg_names[pos_offset:], defaults):
        assert name not in res
        res[name] = value
    return res


# Copy of python3.7.2's typing.ForwardRef -- currently no changes to it.
class ForwardRef:
    """Internal wrapper to hold a forward reference."""

    __slots__ = ('__forward_arg__', '__forward_code__',
                 '__forward_evaluated__', '__forward_value__',
                 '__forward_is_argument__')

    def __init__(self, arg, is_argument=True):
        if not isinstance(arg, str):
            raise TypeError(f"Forward reference must be a string -- got {arg!r}")
        try:
            code = compile(arg, '<string>', 'eval')
        except SyntaxError:
            raise SyntaxError(f"Forward reference must be an expression -- got {arg!r}")
        self.__forward_arg__ = arg
        self.__forward_code__ = code
        self.__forward_evaluated__ = False
        self.__forward_value__ = None
        self.__forward_is_argument__ = is_argument

    def _evaluate(self, globalns, localns):
        if not self.__forward_evaluated__ or localns is not globalns:
            if globalns is None and localns is None:
                globalns = localns = {}
            elif globalns is None:
                globalns = localns
            elif localns is None:
                localns = globalns
            self.__forward_value__ = _type_check(
                eval(self.__forward_code__, globalns, localns),
                "Forward references must evaluate to types.",
                is_argument=self.__forward_is_argument__)
            self.__forward_evaluated__ = True
        return self.__forward_value__

    def __eq__(self, other):
        if not isinstance(other, ForwardRef):
            return NotImplemented
        return (self.__forward_arg__ == other.__forward_arg__ and
                self.__forward_value__ == other.__forward_value__)

    def __hash__(self):
        return hash((self.__forward_arg__, self.__forward_value__))

    def __repr__(self):
        return f'ForwardRef({self.__forward_arg__!r})'


# Copy of python3.7.2's typing but removing the private typing references
# (which just produce error cases)
def _type_check(arg, msg, is_argument=True):
    """Check that the argument is a type, and return it (internal helper).

    As a special case, accept None and return type(None) instead. Also wrap strings
    into ForwardRef instances. Consider several corner cases, for example plain
    special forms like Union are not valid, while Union[int, str] is OK, etc.
    The msg argument is a human-readable error message, e.g::

        "Union[arg, ...]: arg should be a type."

    We append the repr() of the actual value (truncated to 100 chars).
    """

    if arg is None:
        return type(None)
    if isinstance(arg, str):
        return ForwardRef(arg)
    # TODO(lincoln): in the python version of typing, we exclude certain typing special
    # forms which are not types (like plain Union, etc.), and raise TypeErrors.
    # We should probably do that here too, but without using anything internal from typing.
    if isinstance(arg, (type, TypeVar, ForwardRef)):
        return arg
    if not callable(arg):
        raise TypeError(f"{msg}: Got {arg!r:.100}.")
    return arg


def is_forward_ref(t) -> bool:
    """Returns true if `t` is a ForwardRef (either the one we define, or the one in `typing`.)."""
    from typing import ForwardRef as TypingForwardRef
    return isinstance(t, ForwardRef) or isinstance(t, TypingForwardRef)

def get_forward_ref_str(t):
    """If `t` is a ForwardRef, returns the interior string for that ForwardRef."""
    return t.__forward_arg__