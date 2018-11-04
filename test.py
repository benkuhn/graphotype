import main
import graphql

class Query(main.GQLObject):
    def c(self, d: bool, e: float) -> 'Foo':
        return Foo(7 if d else int(e), str(d))

class Foo(main.GQLObject):
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b
    a: int
    b = 'foo'


schema = main.make_schema(query=Query, mutation=None)

print(graphql.print_schema(schema))

query = '''
query {
    c(d: true, e: 1.0) {
        a
    }
}
'''

import json
print('Data:', json.dumps(graphql.graphql(schema, query).data, indent=2))
print('Errors:', graphql.graphql(schema, query).errors)
