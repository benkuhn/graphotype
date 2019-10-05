"""graphene <> graphotype interop for incremental migration."""

from graphql.type.definition import GraphQLNamedType, GraphQLNonNull

from graphotype.types import Annotation, AClass
from . import SchemaCreator, Object

import graphene.types.typemap


class InteropTypeMap(graphene.types.typemap.TypeMap):
    def __init__(self, sc: SchemaCreator):
        self.sc = sc
        super().__init__([])

    def reducer(self, map, type):
        assert map is self.sc.name_map
        if issubclass(type, Object):
            self.sc.translate_annotation_unwrapped(AClass(None, type, None))
            return map
        return super().reducer(map, type)

    def get_field_type(self, map, type):
        assert map is self.sc.name_map
        if issubclass(type, Object):
            return map[type.__name__]
        return super().get_field_type(map, type)


class Adapter(SchemaCreator):
    def __init__(self, query):
        super().__init__(query, None, [])
        self.name_map = {}

    def adapt(self, t):
        return self.translate_type(t).of_type

    def translate_type(self, t):
        if issubclass(t, graphene.ObjectType):
            tm = InteropTypeMap(self)
            self.name_map = tm.graphene_reducer(self.name_map, t)
            return GraphQLNonNull(self.name_map[t._meta.name])
        return super().translate_type(t)

    def translate_annotation_unwrapped(self, ann: Annotation) -> GraphQLNamedType:
        result = super().translate_annotation_unwrapped(ann)
        self.name_map[result.name] = result
        return result

    @property
    def schema(self):
        return self.build()
