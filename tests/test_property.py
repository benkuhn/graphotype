from typing import List
import json

from dataclasses import dataclass, asdict
from graphotype import make_schema
from graphql import graphql

def test_property():
    class Query:
        @property
        def anInt(self) -> int:
            return 1

    schema = make_schema(Query)
    result = graphql(schema, 'query { anInt }', root=Query())
    assert not result.errors
    assert result.data == dict(anInt=1)
