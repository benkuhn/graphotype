from typing import Optional, Union

from graphql import graphql
from graphotype import make_schema, Object

import pytest

class Foo(Object):
    i: int = 1

class Bar(Object):
    b: str = 'b'

MyUnion = Union[Foo, Bar]
OptMyUnion = Optional[MyUnion]

class Query(Object):
    requiredFoo: MyUnion = Foo()
    requiredBar: MyUnion = Bar()
    optionalFoo: OptMyUnion = None
    optionalBar: OptMyUnion = None

@pytest.fixture(scope='module')
def schema():
    yield make_schema(
        query=Query, unions={'MyUnion': MyUnion})

def test_requiredInt(schema):
    result = graphql(schema, '''query {
        requiredFoo { ... F ... B }
        requiredBar { ... F ... B }
        optionalFoo { ... F ... B }
        optionalBar { ... F ... B }
    }
    fragment F on Foo { i }
    fragment B on Bar { b }
    ''', root=Query())
    assert not result.errors
    assert result.data == {
        'requiredFoo': { 'i': 1 },
        'requiredBar': { 'b': 'b' },
        'optionalFoo': None,
        'optionalBar': None
    }
