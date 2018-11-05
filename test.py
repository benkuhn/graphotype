import dataclasses
import main
import graphql
import enum
from typing import Iterable, Optional, NewType, Union

class MyEnum(enum.Enum):
    GIRAFFES = 1
    ZEBRAS = 2

class MyInterface(main.GQLInterface):
    abstract: Optional[str]

class ImplOne(MyInterface):
    abstract = 'yes'

class ImplTwo(MyInterface):
    abstract = 'no'

@dataclasses.dataclass
class Input(main.GQLInput):
    a: int
    b: Optional[MyEnum]
    c: int = 1

class Query(main.GQLObject):
    def c(self, d: bool, e: float) -> 'Foo':
        return Foo(7 if d else int(e), str(d))

    def isGiraffes(self, g: MyEnum) -> bool:
        return g == MyEnum.GIRAFFES

    def unionReturner(self) -> 'MyUnion':
        return Bar()

    def interfaceReturner(self) -> 'MyInterface':
        return ImplOne()

    def process(self, input: Input) -> bool:
        print(input.a, input.b, input.c)
        return True

class Foo(main.GQLObject):
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b
    a: Optional[int]
    b = 'foo'
    c = MyEnum.GIRAFFES
    def d(self) -> Iterable[int]:
        yield 1
        yield 2
        yield 3

class Bar(main.GQLObject):
    a: main.ID = 'a'

MyUnion = NewType('MyUnion', Union[Foo, Bar])

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
    unionReturner {
        ...on Bar {
            a
        }
    }
    interfaceReturner {
        abstract
    }
    process(input: {a: 1, b: GIRAFFES, c: 1})
}
'''

import json
result = graphql.graphql(schema, query)
print('Data:', json.dumps(result.data, indent=2))
print('Errors:', result.errors)
