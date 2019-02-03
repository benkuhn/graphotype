from typing import Type, List, Iterable, Iterator, Optional, Any, Dict, get_type_hints, Union

try:
    from typing import ForwardRef
except ImportError:
    # python 3.6 I guess?
    class ForwardRef: pass

from dataclasses import dataclass
import typing_inspect

NoneType = type(None)

@dataclass
class AnnotationOrigin:
    """Where did this Annotation come from? (classname.fieldname)

    Used only for printing error messages.
    """
    classname: str
    fieldname: str

@dataclass
class Annotation:
    t_raw: Optional[Any]
    t: Type
    origin: Optional[AnnotationOrigin]
    @property
    def name(self) -> Optional[str]:
        return self.t_raw if isinstance(self.t_raw, str) else None

@dataclass
class AUnion(Annotation):
    """Union[x, y, ...] that is not an Optional"""
    of_types: List[Annotation]

@dataclass
class AList(Annotation):
    """List[x]"""
    of_type: Annotation

@dataclass
class AOptional(Annotation):
    """Optional[x]"""
    of_type: Annotation

@dataclass
class ANewType(Annotation):
    """NewType of another Annotation.

    This uses the same python implementation with a different GraphQL type."""
    of_type: Annotation
    @property
    def typename(self):
        return self.t.__name__

@dataclass
class AClass(Annotation):
    """Everything else (Python class -- this can be scalars and object types)"""
    @property
    def typename(self):
        return self.t.__name__

def _get_newtype_of(t: Type) -> Optional[Type]:
    if not hasattr(t, '__supertype__'):
        return None
    ret = t.__supertype__
    # ret might itself be a newtype
    ret_of = _get_newtype_of(ret)
    if ret_of is not None:
        return ret_of
    return ret

def _get_iterable_of(t: Type) -> Optional[Type]:
    if not typing_inspect.is_generic_type(t):
        return None
    origin = typing_inspect.get_origin(t)
    args = typing_inspect.get_args(t)
    if origin in (list, List, Iterable, Iterator):
        return args[0]
    return None

def make_annotation(raw: Optional[Any], parsed: Type, origin: Optional[AnnotationOrigin] = None) -> Annotation:
    """Recursively transform a Python type hint into an Annotation for our schema.

    'parsed' should be a result of typing.get_type_hints on something.
    'raw', if available, should be the string annotation from __annotations__.

    This is recursive because a type like Union or List references other types.
    """
    if typing_inspect.is_union_type(parsed):
        args = typing_inspect.get_args(parsed, evaluate=True)
        # If is_optional is true, wrap the union in an Optional at the end.
        is_optional = NoneType in args

        args = [arg for arg in args if arg != NoneType]

        # Try and unwrap the outermost thing in `raw` because it may be useful later. If we fail, that's ok,
        # we can fallback to None.
        unwrapped_raw = _unwrap_outer_nullable(raw)

        if len(args) == 1:
            raw_args = [unwrapped_raw]
        else:
            raw_args = [None] * len(args)

        of_types = [
            make_annotation(t_raw, t, origin)
            for t_raw, t in zip(raw_args, args)
        ]

        if len(of_types) == 1:
            [ann] = of_types
        else:
            ann = AUnion(
                # interpret 'is_optional' being true as meaning we should use the unwrapped raw
                # this enables Optional[MyUnion] to work
                t_raw=unwrapped_raw if is_optional else raw,
                t=Union[tuple(args)],
                of_types=of_types,
                origin=origin
            )
        if is_optional:
            ann = AOptional(
                t_raw=raw, t=parsed, of_type=ann, origin=origin
            )
        return ann
    nt_of = _get_newtype_of(parsed)
    if nt_of is not None:
        return ANewType(
            t_raw=raw,
            t=parsed,
            of_type=make_annotation(None, nt_of, origin),
            origin=origin
        )
    iter_of = _get_iterable_of(parsed)
    if iter_of is not None:
        return AList(
            t_raw=raw,
            t=parsed,
            of_type=make_annotation(_unwrap_outer_nullable(raw), iter_of, origin),
            origin=origin
        )
    if isinstance(parsed, type):
        return AClass(
            t_raw=raw,
            t=parsed,
            origin=origin
        )
    raise ValueError(f"Don't understand type {parsed}")


class UnwrapException(Exception): pass


def _unwrap_outer_str(raw: str) -> str:
    """Parse and unwrap the outermost type and 1 layer of brackets from `raw`,
     returning whatever is inside the outermost brackets.
     """

    import re
    result = re.match(r'^\s*[_a-zA-Z][_a-zA-Z0-9]*\s*\[(.+)\]\s*$', raw, re.DOTALL)
    if not result:
        raise UnwrapException(f"unable to match unwrap pattern: {repr(raw)}")

    return result.group(1).strip()


def _unwrap_outer(raw: Any) -> Any:
    """Unwrap one layer of type wrapper from 'raw', which is the raw
    annotation value from __annotations__ (which should only be a String,
    or either an Optional or List).

    If `raw` is a string, we use unwrap_outer_str.

    If we fail, raises UnwrapException
    """
    if isinstance(raw, str):
        # If given 'Optional[foo]', give back 'foo'.
        return _unwrap_outer_str(raw)

    if typing_inspect.is_union_type(raw):
        # If given Optional['foo'], give back 'foo'.
        # If given Optional[foo], give back foo.
        # If given Union[int, str], throw.
        raw_args = [x for x in typing_inspect.get_args(raw) if x is not NoneType]
        if len(raw_args) != 1:
            raise UnwrapException(f"Unwrap_outer ran into a Union: {raw}")

    else:
        raw_args = typing_inspect.get_args(raw)

    if len(raw_args) != 1:
        raise UnwrapException(f"Unwrap_outer doesn't know what to do with {len(raw_args)}-arg type: {raw}")

    arg = raw_args[0]

    if isinstance(arg, ForwardRef):
        # In python3.7, we (might) sometimes get ForwardRefs in here. Unwrap to get the name in that case
        return arg.__forward_arg__
    else:
        return arg


def _unwrap_outer_nullable(raw: Any) -> Any:
    """Same as _unwrap_outer, but catch UnwrapException and return None."""
    try:
        return _unwrap_outer(raw)
    except UnwrapException:
        return None


def get_annotations(o: Any) -> Dict[str, Annotation]:
    """Call get_type_hints on 'o', wrapping the resulting annotations.

    The resulting hints are wrapped in our own Annotation instances."""
    ret = {}
    for k, t in get_type_hints(o).items():
        origin = AnnotationOrigin(repr(o), k)
        t_raw = o.__annotations__.get(k)
        ret[k] = make_annotation(t_raw, t, origin)
    return ret
