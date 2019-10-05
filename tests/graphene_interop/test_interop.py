
import graphene as gn
import graphotype as gt
from graphql import graphql

from graphotype.graphene import InteropSchemaCreator

def test_basic_interop():
    class Query(gn.ObjectType):
        graphotype = gn.Field(lambda: Graphotype)

        def resolve_hello(root, info, name):
            return f'Hello {name}!'

        def resolve_graphotype(root, info):
            return Graphotype()

    class SubObject(gn.ObjectType):
        goodbye = gn.String()

    class Graphotype(gt.Object):
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

