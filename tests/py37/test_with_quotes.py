from __future__ import annotations

from typing import Union

"""Tests that include quotes in the type annotations
(even though you don't need to use quotes under PEP563)
"""

from graphql import graphql

from graphotype import Object, make_schema


class Left(Object):
    name: str

class Right(Object):
    value: int

Either = Union[Left, Right]

class Query(Object):
    x: 'int' = 0
    @property
    def y(self) -> 'int':
        return 0

    @property
    def z(self) -> 'Either':
        return Right('it works')

    w: Either

def test_self_reference():

    schema = make_schema(Query)
    result = graphql(schema, 'query { x, y }', root=Query())
    assert not result.errors
    assert result.data == {'x': 0, 'y': 0}
