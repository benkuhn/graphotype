
import graphene as gn
import graphotype as gt
from graphql import graphql

from graphotype.graphene import InteropSchemaCreator, InteropInterface

class Query(gt.Object):

    def interface(self) -> 'Iface':
        return GtImpl()

    def interface2(self) -> 'Iface':
        return GnImpl()

    hack: 'GtImpl'
    hack2: 'GnImpl'


class Iface(InteropInterface):
    value: int


class GnImpl(gn.ObjectType):
    class Meta:
        interfaces = (Iface, )

    value = gn.Int()

    def resolve_value(self, info):
        return 5


class GtImpl(gt.Object):
    value = 5


def test_cross_boundary_implementation():
    """Test that gt objects can implement gn interfaces"""

    schema = InteropSchemaCreator(Query).build()

    result = graphql(schema, '{ interface { value }}')
    assert not result.errors
    assert result.data == {'interface': {'value': 5}}
