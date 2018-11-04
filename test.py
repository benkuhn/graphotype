import main
import graphql
import enum
from typing import List

class MyEnum(enum.Enum):
    GIRAFFES = 1
    ZEBRAS = 2

class Query(main.GQLObject):
    def c(self, d: bool, e: float) -> 'Foo':
        return Foo(7 if d else int(e), str(d))

    def isGiraffes(self, g: MyEnum) -> bool:
        return g == MyEnum.GIRAFFES

class Foo(main.GQLObject):
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b
        self.d = [1,2,3]
    a: int
    b = 'foo'
    c = MyEnum.GIRAFFES
    d: List[int]


schema = main.make_schema(query=Query, mutation=None)

print(graphql.print_schema(schema))

query = '''
query {
    c(d: true, e: 1.0) {
        a
        c
        d
    }
    isGiraffes(g: GIRAFFES)
}
'''

import json
print('Data:', json.dumps(graphql.graphql(schema, query).data, indent=2))
print('Errors:', graphql.graphql(schema, query).errors)
