"""graphene <> graphotype interop for mostly-seamless incremental migration.

# Usage

1. Replace `SchemaCreator` with `InteropSchemaCreator`:

        schema = InteropSchemaCreator(Query).build()

2. Use any Graphene type name where you would normally use a Graphotype type name, or
vice versa:

    ```
    class GrapheneObject(graphene.ObjectType):
        graphotype_field = Field(lambda: GraphotypeObject)
        def resolve_graphotype_field(self):
            return GraphotypeObject()

    class GraphotypeObject(graphotype.Object):
        @property
        def graphene_field(self) -> GrapheneObject:
            return GrapheneObject()
    ```

# Implementation notes

There are 2 main differences between the way Graphene and Graphotype do the job of
"type mapping," that is, taking in a set of Python objects and outputting a set of
GraphQLType instances.

1. graphotype uses a single, mutable dict (SchemaCreator.type_map) to store the
registry of mapped types, which is updated as it visits each Python type. Graphene
uses a "reduce" operation with the type signature (map, python_type) -> new_map.

    (Luckily for us, though, the so-called reducer actually always just mutates the
    input map, rather than returning a new map.)

2. graphotype's type map is a Dict[Type, GraphQLType], whereas graphene's type map is
a Dict[str, GraphQLType] (where the string is a typename).

To get interop between Graphotype types and Graphene types, we thus build two new
classes:

- `InteropSchemaCreator`, a `graphotype.SchemaCreator` subclass which:

    - maintains a Dict[str, GraphQLType] of gqltypes-by-name in addition to its normal
      dict of gqltypes-by-pythontype

    - knows how to interpret Graphene objects in type annotations.

- `InteropTypeMap`, a subclass of `graphene.types.typemap.TypeMap` which knows how to
understand graphotype types in `graphene.Field` instances.

"""
from typing import Type, List

from graphql.type.definition import GraphQLNamedType, GraphQLNonNull, \
    GraphQLInterfaceType

from . import types, Interface
from . import SchemaCreator, Object

import graphene.types.typemap


class InteropTypeMap(graphene.types.typemap.TypeMap):
    def __init__(self, sc: SchemaCreator):
        self.sc = sc
        super().__init__([])

    def reducer(self, map, type):
        assert map is self.sc.name_map
        if issubclass(type, Object):
            # Put `type` in the SchemaCreator's typemap.
            self.sc.translate_annotation_unwrapped(types.AClass(None, type, None))
            return map
        return super().reducer(map, type)

    def get_field_type(self, map, type):
        assert map is self.sc.name_map
        if issubclass(type, Object):
            return map[type.__name__]
        return super().get_field_type(map, type)


class InteropSchemaCreator(SchemaCreator):
    def __init__(self, query):
        super().__init__(query, None, [])
        self.name_map = {}

    def adapt(self, t):
        return self.translate_type(t).of_type

    def translate_type(self, t):
        if graphene.types.typemap.is_graphene_type(t):
            tm = InteropTypeMap(self)
            new_name_map = tm.graphene_reducer(self.name_map, t)
            assert new_name_map is self.name_map
            return GraphQLNonNull(self.name_map[t._meta.name])
        return super().translate_type(t)

    def translate_annotation_unwrapped(self, ann: types.Annotation) -> GraphQLNamedType:
        result = super().translate_annotation_unwrapped(ann)
        self.name_map[result.name] = result
        return result

    def map_interface(self, cls: Type[Interface]) -> GraphQLInterfaceType:
        graphene_type = getattr(cls, '__graphene_equivalent__')
        if graphene_type is not None:
            tm = InteropTypeMap(self)
            new_name_map = tm.graphene_reducer(self.name_map, graphene_type)
            assert new_name_map is self.name_map
            return self.name_map[graphene_type._meta.name]
        return super().map_interface(cls)

    @property
    def schema(self):
        return self.build()


class InteropInterface(Interface, graphene.Interface):

    def __init__(self) -> None:
        pass
