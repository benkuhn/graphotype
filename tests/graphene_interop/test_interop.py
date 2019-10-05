
from graphene import ObjectType, String, Schema, Field
from graphotype import Object


class SubObject(ObjectType):
    goodbye = String()


class Graphotype(Object):
    @property
    def a_property(self) -> str:
        return 'value'

    @property
    def a_subobject(self) -> SubObject:
        return SubObject(goodbye='See ya!')


class Query(ObjectType):
    # this defines a Field `hello` in our Schema with a single Argument `name`
    hello = String(name=String(default_value="stranger"))
    graphotype = Field(Graphotype)

    # our Resolver method takes the GraphQL context (root, info) as well as
    # Argument (name) for the Field and returns data for the query Response
    def resolve_hello(root, info, name):
        return f'Hello {name}!'

    def resolve_graphotype(root, info):
        return Graphotype()


schema = Schema(query=Query)

def test_interop():
    result = schema.execute('{ graphotype { a_property, a_subobject { goodbye } }')
