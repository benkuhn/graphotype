
import graphene as gn
import graphotype as gt
from graphql import graphql

from graphotype.graphene import InteropSchemaCreator, InteropInterface

class Query(gt.Object):

    def gtVal(self) -> 'Node':
        return GtImpl()

    def gnVal(self) -> 'Node':
        return GnImpl()

    hack: 'GtImpl'
    hack2: 'GnImpl'


class Node(gn.Interface):
    value = gn.Int()
GnNode = Node

class Node(gt.Interface):
    __graphene_equivalent__ = GnNode
    value: int


class GnImpl(gn.ObjectType, Node):
    class Meta:
        interfaces = (GnNode, )

    value = gn.Int()

    def resolve_value(self, info):
        return 5


class GtImpl(gt.Object, Node):
    value = 6


def test_cross_boundary_implementation():
    """Test that gt objects can implement gn interfaces"""

    schema = InteropSchemaCreator(Query).build()

    result = graphql(schema, '{ gtVal { value } gnVal { value }}')
    assert not result.errors
    assert result.data == {'gtVal': {'value': 6}, 'gnVal': {'value': 5}}

    result = graphql(schema, '{ __type(name: "Node") { possibleTypes { name } } }')
    assert not result.errors
    print(result.data)
    assert result.data['__type']['possibleTypes'] == [
        {'name': 'GtImpl'}, {'name': 'GnImpl'}
    ]
