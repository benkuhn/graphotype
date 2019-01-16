from typing import Type, NamedTuple, List, Iterable, Iterator, Optional, Any, Dict, get_type_hints, Union

from dataclasses import dataclass
import typing_inspect

NoneType = type(None)

@dataclass
class Annotation:
    t_raw: Optional[Any]
    t: Type
    @property
    def name(self) -> Optional[str]:
        return self.t_raw if isinstance(self.t_raw, str) else None

@dataclass
class AUnion(Annotation):
    of_types: List[Annotation]

@dataclass
class AList(Annotation):
    of_type: Annotation

@dataclass
class AOptional(Annotation):
    of_type: Annotation

@dataclass
class ANewType(Annotation):
    of_type: Annotation
    @property
    def typename(self):
        return self.t.__name__

@dataclass
class AClass(Annotation):
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

def make_annotation(raw: Optional[Any], parsed: Type) -> Annotation:
    if typing_inspect.is_union_type(parsed):
        args = typing_inspect.get_args(parsed, evaluate=True)
        is_optional = NoneType in args
        args = [arg for arg in args if arg != NoneType]
        # special case to ensure Optional['foo'].of_type.name == 'foo' etc.
        if typing_inspect.is_union_type(raw):
            raw_args = typing_inspect.get_args(raw)
            of_types = [
                make_annotation(t_raw, t)
                for t_raw, t in zip(raw_args, args)
            ]
        else:
            of_types = [make_annotation(None, t) for t in args]
        if len(of_types) == 1:
            [ann] = of_types
        else:
            ann = AUnion(
                t_raw=None if is_optional else raw,
                t=Union[tuple(args)],
                of_types=of_types
            )
        if is_optional:
            ann = AOptional(
                t_raw=raw, t=parsed, of_type=ann
            )
        return ann
    nt_of = _get_newtype_of(parsed)
    if nt_of is not None:
        return ANewType(
            t_raw=raw,
            t=parsed,
            of_type=make_annotation(None, nt_of)
        )
    iter_of = _get_iterable_of(parsed)
    if iter_of is not None:
        return AList(
            t_raw=raw,
            t=parsed,
            of_type=make_annotation(None, iter_of)
        )
    if isinstance(parsed, type):
        return AClass(
            t_raw=raw,
            t=parsed
        )
    raise ValueError("Don't understand type {type}")



def get_annotations(o: Any) -> Dict[str, Annotation]:
    ret = {}
    for k, t in get_type_hints(o).items():
        t_raw = o.__annotations__.get(k)
        ret[k] = make_annotation(t_raw, t)
    return ret
