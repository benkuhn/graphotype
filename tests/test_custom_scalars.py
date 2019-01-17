import json
from typing import NewType, Any, Optional
from datetime import datetime, timezone

from graphql import graphql
from graphotype import make_schema, Object, Scalar

import pytest

FakeInt = NewType('FakeInt', int)
FakeDateTime = NewType('FakeDateTime', datetime)

_FORMAT = '%Y-%m-%d %H:%M:%S'

class DateTime(Scalar[datetime]):
    t = datetime

    @classmethod
    def parse(cls, value: Any) -> datetime:
        return datetime.strptime(value, _FORMAT)

    @classmethod
    def serialize(cls, instance: datetime) -> Any:
        return instance.strftime(_FORMAT)

class JSON(Scalar[dict]):
    t = dict

    @classmethod
    def parse(cls, value: Any) -> datetime:
        return dict(value)

_DATETIME = datetime(2019, 1, 10, 23, 35, 7)
_DATETIME_STR = DateTime.serialize(_DATETIME)

class Query(Object):
    fake: FakeInt = FakeInt(1)
    dt: datetime = _DATETIME
    fakeDt: FakeDateTime = FakeDateTime(_DATETIME)
    def subquery(self) -> 'Optional[SubQuery]':
        return SubQuery(self)
    def add(self, f: FakeInt, dt: datetime) -> FakeInt:
        return FakeInt(int(dt.replace(tzinfo=timezone.utc).timestamp())) + f
    def dumps(self, obj: dict) -> str:
        return json.dumps(obj, sort_keys=True, indent=2)

SubQuery = NewType('SubQuery', Query)

@pytest.fixture(scope='module')
def schema():
    yield make_schema(
        query=Query, scalars=[DateTime, JSON])

def test_newtype_object(schema):
    result = graphql(schema, '''query {
        __schema { queryType { fields { name, type { name }}}}
    }''')
    assert not result.errors
    fields = result.data['__schema']['queryType']['fields']
    subquery = next(f for f in fields if f['name'] == 'subquery')
    assert subquery == dict(name='subquery', type=dict(name='Query'))

def test_newtype_scalar_output(schema):
    result = graphql(schema, '''query {
        fake
    }''', root=Query())
    assert not result.errors
    assert result.data == { 'fake': 1 }

def test_custom_scalar_output(schema):
    result = graphql(schema, '''query {
        dt
    }''', root=Query())
    assert not result.errors
    assert result.data == { 'dt': _DATETIME_STR }

def test_newtype_of_custom_scalar_output(schema):
    result = graphql(schema, '''query {
        fakeDt
    }''', root=Query())
    assert not result.errors
    assert result.data == { 'fakeDt': _DATETIME_STR }

def test_custom_scalar_from_ast(schema):
    result = graphql(schema, '''query {
        add(f: 1, dt: "2019-01-10 23:35:07")
    }''', root=Query())
    assert not result.errors
    assert result.data == { 'add': 1547163308 }

def test_custom_scalar_from_values(schema):
    result = graphql(schema, '''query Q($f: FakeInt!, $dt: DateTime!) {
        add(f: $f, dt: $dt)
    }''', variable_values=dict(f=1, dt=_DATETIME_STR), root=Query())
    assert not result.errors
    assert result.data == { 'add': 1547163308 }

def test_dict_and_list_from_ast(schema):
    result = graphql(schema, '''query {
        dumps(obj: {innerObj: {a: 1}, innerList: ["bar"]} )
    }''', root=Query())
    assert not result.errors
    assert result.data == {
        'dumps': '{\n'
                 '  "innerList": [\n'
                 '    "bar"\n'
                 '  ],\n'
                 '  "innerObj": {\n'
                 '    "a": "1"\n'
                 '  }\n'
                 '}'}
