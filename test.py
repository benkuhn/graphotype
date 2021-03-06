import dataclasses
from datetime import datetime
import graphotype
import graphql
import enum
from typing import Iterable, Optional, NewType, Union, List
import traceback

class MyEnum(enum.Enum):
    GIRAFFES = 1
    ZEBRAS = 2

class MyInterface(graphotype.Interface):
    abstract: Optional[str]

class ImplOne(graphotype.Object, MyInterface):
    abstract = 'yes'

class ImplTwo(graphotype.Object, MyInterface):
    abstract = 'no'

@dataclasses.dataclass
class Input:
    a: int
    b: Optional[MyEnum]
    c: int = 1

class Query(graphotype.Object):
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

    def now(self, a_date: datetime) -> datetime:
        assert isinstance(a_date, datetime)
        return datetime.now()

class Foo(graphotype.Object):
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b
    a: Optional[int]
    b = 'foo'
    c = MyEnum.GIRAFFES
    def d(self) -> List[int]:
        return [1,2,3]

class Bar(graphotype.Object):
    a: graphotype.ID = 'a'

class Date(graphotype.Scalar):
    t = datetime
    _format = '%Y-%m-%d %H:%M:%S'
    @classmethod
    def serialize(cls, instance: datetime) -> str:
        return instance.strftime(cls._format)
    @classmethod
    def parse(cls, value: str) -> datetime:
        return datetime.strptime(value, cls._format)


MyUnion = Union[Foo, Bar]

schema = graphotype.make_schema(query=Query, mutation=None, scalars=[Date])

if __name__ == '__main__':
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
        now(a_date: "2018-01-01 02:33:44")
    }
    '''

    import json
    result = graphql.graphql(schema, query)
    print('Data:', json.dumps(result.data, indent=2))
    print('Errors:', result.errors)

    if result.errors:
        for e in result.errors:
            traceback.print_exception(type(e), e, e.__traceback__)
