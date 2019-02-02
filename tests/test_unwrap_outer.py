from typing import List, Optional, Union

import pytest

from graphotype.types import _unwrap_outer, UnwrapException


def test_unwrap_outer_str_basics():
    assert _unwrap_outer("Optional[int]") == 'int'
    assert _unwrap_outer("List[int]") == 'int'
    assert _unwrap_outer("Optional[List[int]]") == 'List[int]'
    assert _unwrap_outer("List[Optional[int]]") == 'Optional[int]'


def test_unwrap_outer_str_strips_whitespace():
    assert _unwrap_outer("List[  int   ]") == 'int'
    assert _unwrap_outer(" List [int] ") == 'int'
    assert _unwrap_outer("\nList [int\n\t] ") == 'int'
    assert _unwrap_outer(_unwrap_outer("\nList[  Optional  [    int\n\t   ] ] ")) == 'int'


def test_unwrap_outer_evald_types():
    assert _unwrap_outer(List[int]) == int
    assert _unwrap_outer(Optional[int]) == int
    assert _unwrap_outer(List[Optional[int]]) == Optional[int]

    assert _unwrap_outer(List['int']) == 'int'
    assert _unwrap_outer(Optional['int']) == 'int'
    assert _unwrap_outer(List['Optional[int]']) == 'Optional[int]'
    assert _unwrap_outer(List[Optional['int']]) == Optional['int']


def test_unwrap_around_union():
    MyUnion = Union[str, int]
    assert _unwrap_outer(List[MyUnion]) == MyUnion
    assert _unwrap_outer(List['MyUnion']) == 'MyUnion'


def test_cant_unwrap_union_directly():
    MyUnion = Union[str, int]
    with pytest.raises(UnwrapException):
        _unwrap_outer(MyUnion)
