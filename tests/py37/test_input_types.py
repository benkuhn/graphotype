from __future__ import annotations

from typing import List
import json

from dataclasses import dataclass, asdict
from graphotype import make_schema, Object
from graphql import graphql

# With PEP563, we need to define dependencies outside functions
@dataclass
class SubInput:
    aList: List[int]

@dataclass
class MyInput:
    anInt: int
    aStr: str
    aSubInput: SubInput


def test_input_type():
    class Query(Object):
        def serialize(self, i: MyInput) -> str:
            return json.dumps(asdict(i), sort_keys=True, indent=2)

    schema = make_schema(Query)
    result = graphql(schema, '''
    query { serialize(i: {
        anInt: 1, aStr: "asdf", aSubInput: { aList: [1, 2, 3] }
    }) }''')
    assert not result.errors
    assert result.data['serialize'] == '''
{
  "aStr": "asdf",
  "aSubInput": {
    "aList": [
      1,
      2,
      3
    ]
  },
  "anInt": 1
}
'''.strip()
