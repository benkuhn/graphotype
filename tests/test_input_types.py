from typing import List
import json

from dataclasses import dataclass, asdict
from graphotype import make_schema
from graphql import graphql

def test_input_type():
    @dataclass
    class SubInput:
        aList: List[int]

    @dataclass
    class MyInput:
        anInt: int
        aStr: str
        aSubInput: SubInput

    class Query:
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
