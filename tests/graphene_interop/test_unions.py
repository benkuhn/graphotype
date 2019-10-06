from typing import Union

import graphene as gn
import graphotype as gt
from graphql import graphql

from graphotype.graphene import InteropSchemaCreator

from tests.helpers import execute


class Query(gt.Object):

    def graphene(self) -> 'Either':
        return Graphene()

    def graphotype(self) -> 'Either':
        return Graphotype()


class Graphene(gn.ObjectType):
    hello = gn.String()

    def resolve_hello(self, info):
        return 'world'


class Graphotype(gt.Object):
    hi = 'hi there'


Either = Union[Graphene, Graphotype]


def test_cross_boundary_implementation():
    """Test that gt objects can implement gn interfaces"""

    schema = InteropSchemaCreator(Query).build()

    result = execute(schema, '''{
    graphene { ...on Graphene { hello } ...on Graphotype { hi } }
    graphotype { ...on Graphotype { hi } }}
    ''')
    assert result == {'graphene': {'hello': 'world'}, 'graphotype': {'hi': 'hi there'}}

    result = execute(schema, '{ __type(name: "Either") { possibleTypes { name } } }')
    assert set(x['name'] for x in result['__type']['possibleTypes']) == {'Graphene', 'Graphotype'}
