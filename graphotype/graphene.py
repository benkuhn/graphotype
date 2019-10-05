from graphql.type.definition import GraphQLNamedType

from . import SchemaCreator

import graphene.types.typemap

old_get_field_type = graphene.types.typemap.TypeMap.get_field_type

def new_get_field_type(self, map, type):
    if isinstance(type, GraphQLNamedType):
        return type
    return old_get_field_type(self, map, type)

graphene.types.typemap.TypeMap.get_field_type = new_get_field_type


class Adapter(SchemaCreator):
    def __init__(self, query):
        super().__init__(None, None, [])
        self.query = query

    def adapt(self, t):
        return self.translate_type(t).of_type

    def translate_type(self, t):
        if issubclass(t, graphene.ObjectType):
            return t
        return super().translate_type(t)

    @property
    def schema(self):
        return graphene.Schema(query=self.query)
