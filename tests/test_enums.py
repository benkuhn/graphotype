import enum
from typing import Optional, Union

from graphql import graphql
from graphotype import make_schema, Object

import pytest

class MyEnum(enum.Enum):
    ONE = 1
    TWO = 2

class Query(Object):
    val: MyEnum = MyEnum.ONE
    def f(self, val: MyEnum) -> int:
        return val.value

@pytest.fixture(scope='module')
def schema():
    yield make_schema(query=Query)

def test_return_enum(schema):
    result = graphql(schema, 'query { val }', root=Query())
    assert not result.errors
    assert result.data == {
        'val': 'ONE'
    }

def test_enum_arg_ast(schema):
    result = graphql(schema, 'query { f(val: ONE) }', root=Query())
    assert not result.errors
    assert result.data == {
        'f': 1
    }

def test_enum_arg_var(schema):
    result = graphql(
        schema,
        'query Q ($e: MyEnum!) { f(val: $e) }',
        root=Query(),
        variable_values={'e': 'TWO'}
    )
    assert not result.errors
    assert result.data == {
        'f': 2
    }
