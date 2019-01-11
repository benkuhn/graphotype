from typing import NewType, Any
from datetime import datetime

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

_DATETIME = datetime(2019, 1, 10, 23, 35, 7)
_DATETIME_STR = DateTime.serialize(_DATETIME)

class Query(Object):
    fake: FakeInt = FakeInt(1)
    dt: datetime = _DATETIME
    fakeDt: FakeDateTime = FakeDateTime(_DATETIME)
    def add(self, f: FakeInt, dt: datetime) -> FakeInt:
        return FakeInt(int(dt.timestamp())) + f

@pytest.fixture(scope='module')
def schema():
    yield make_schema(
        query=Query, scalars=[DateTime])

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
    assert result.data == { 'add': 1547174108 }

def test_custom_scalar_from_values(schema):
    result = graphql(schema, '''query Q($f: FakeInt!, $dt: DateTime!) {
        add(f: $f, dt: $dt)
    }''', variable_values=dict(f=1, dt=_DATETIME_STR), root=Query())
    assert not result.errors
    assert result.data == { 'add': 1547174108 }
