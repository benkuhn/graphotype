from __future__ import annotations

from typing import Optional, Union

from graphql import graphql
from graphotype import make_schema, Object, SchemaError

import pytest

class Foo(Object):
    i: int = 1

class Bar(Object):
    b: str = 'b'

MyUnion = Union[Foo, Bar]

class Query(Object):
    requiredFoo: MyUnion = Foo()
    requiredBar: MyUnion = Bar()
    optionalBar: Optional[MyUnion] = None

@pytest.fixture(scope='module')
def schema():
    yield make_schema(query=Query)

def test_union(schema):
    result = graphql(schema, '''query {
        requiredFoo { ... F ... B }
        requiredBar { ... F ... B }
        optionalBar { ... F ... B }
    }
    fragment F on Foo { i }
    fragment B on Bar { b }
    ''', root=Query())
    assert not result.errors
    assert result.data == {
        'requiredFoo': { 'i': 1 },
        'requiredBar': { 'b': 'b' },
        'optionalBar': None
    }

def test_unnamed_union():
    class Query(Object):
        requiredFoo: Union[int, str]

    with pytest.raises(SchemaError) as e:
        make_schema(Query)
