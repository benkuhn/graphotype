import main
import graphql

class Query(main.GQLObject):
    a: int
    b = 'foo'
    def c(self, d: bool, e: float) -> int:
        pass


schema = main.make_schema(query=Query, mutation=None)

print(graphql.print_schema(schema))
