
from graphene import ObjectType, String, Schema, Field
from graphql import graphql

from graphotype import Object
from graphotype.graphene import InteropSchemaCreator

def test_interop():
    class Query(ObjectType):
        # this defines a Field `hello` in our Schema with a single Argument `name`
        hello = String(name=String(default_value="stranger"))
        graphotype = Field(lambda: Graphotype)

        # our Resolver method takes the GraphQL context (root, info) as well as
        # Argument (name) for the Field and returns data for the query Response
        def resolve_hello(root, info, name):
            return f'Hello {name}!'

        def resolve_graphotype(root, info):
            return Graphotype()

    class SubObject(ObjectType):
        goodbye = String()

    class Graphotype(Object):
        @property
        def a_property(self) -> str:
            return 'value'

        @property
        def a_subobject(self) -> SubObject:
            return SubObject(goodbye='See ya!')

    schema = InteropSchemaCreator(Query).build()

    result = graphql(schema, '{ graphotype { a_property }}')
    assert not result.errors
    assert result.data == {'graphotype': {'a_property': 'value'}}

    result = graphql(schema, '{ graphotype { a_property, a_subobject { goodbye } } }')
    assert not result.errors
    assert result.data == {'graphotype': {'a_property': 'value', 'a_subobject': {'goodbye': 'See ya!'}}}
