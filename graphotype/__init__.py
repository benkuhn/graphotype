from collections import OrderedDict
import dataclasses
import enum
import functools
from typing import (
    Type, get_type_hints, Generic, List, Dict, TypeVar, Any, Callable,
    Union, NewType, Set, Optional, Iterable, FrozenSet
)

from graphql import (
    GraphQLSchema,
    GraphQLObjectType,
    GraphQLInterfaceType,
    GraphQLField,
    GraphQLString,
    GraphQLInt,
    GraphQLBoolean,
    GraphQLFloat,
    GraphQLList,
    GraphQLScalarType,
    GraphQLArgument,
    GraphQLEnumType,
    GraphQLEnumValue,
    GraphQLNonNull,
    GraphQLUnionType,
    GraphQLInputObjectType,
    GraphQLInputObjectField,
    ResolveInfo
)
from graphql.type.definition import GraphQLNamedType
from graphql.language import ast

from . import types

BUILTIN_SCALARS: Dict[Type, GraphQLScalarType] = {
    int: GraphQLInt,
    float: GraphQLFloat,
    str: GraphQLString,
    bool: GraphQLBoolean
}

T = TypeVar('T')
class Scalar(Generic[T]):
    t: Type[T]

    @classmethod
    def parse(cls, value: Any) -> T:
        raise NotImplementedError()

    @classmethod
    def serialize(cls, instance: T) -> Any:
        raise NotImplementedError()

class Object:
    pass

class Interface:
    pass

def unwrap_optional(t: Type) -> Optional[Type]:
    """If t is Optional[foo] for some foo, return foo, otherwise None"""
    assert is_union(t)
    args = t.__args__
    if type(None) not in args:
        return None
    inner_args = set(args) - {type(None)}
    if len(inner_args) == 1:
        return next(iter(inner_args))
    else:
        return Union[tuple(inner_args)]


def is_union(t: Type) -> bool:
    # py36
    #return isinstance(t, _Union)
    return getattr(t, '__origin__', None) == Union

def is_newtype(t: Type) -> bool:
    return hasattr(t, '__supertype__')

def is_iterable_type(t: Type) -> bool:
    # TODO: python3.6 support
    return getattr(t, '__origin__', None) == list

ID = NewType('ID', str)

class WorkingEnumType(GraphQLEnumType):
    def __init__(self, cls: Type[enum.Enum]) -> None:
        self.py_cls = cls
        super().__init__(
            name=cls.__name__,
            description=cls.__doc__,
            values=OrderedDict([
                (v.name, GraphQLEnumValue(v.value))
                for v in cls
            ])
        )

    def parse_literal(self, value_ast: Any) -> enum.Enum:
        value = super().parse_literal(value_ast)
        return self.py_cls(value)

    def parse_value(self, value: str) -> enum.Enum:
        value = super().parse_value(value)
        return self.py_cls(value)

def ast_to_value(node: Any) -> Union[int, float, str, bool, List, Dict]:
    if isinstance(node, (
        ast.IntValue,
        ast.FloatValue,
        ast.StringValue,
        ast.BooleanValue
    )):
        return node.value
    elif isinstance(node, ast.ListValue):
        return [ast_to_value(v) for v in node.values]
    elif isinstance(node, ast.ObjectValue):
        return {field.name.value: ast_to_value(field.value) for field in node.fields}
    else:
        raise NotImplementedError(repr(node))

def make_scalar_map(scalars: List[Type[Scalar]]) -> Dict[Type, GraphQLScalarType]:
    result = {}
    def add_scalar_type(scalar):
        result[scalar.t] = GraphQLScalarType(
            name=scalar.__name__,
            description=scalar.__doc__,
            serialize=scalar.serialize,
            parse_value=lambda val: scalar.parse(val),
            parse_literal=lambda node: scalar.parse(ast_to_value(node))
        )
    for scalar in scalars:
        add_scalar_type(scalar)
    return result

class SchemaCreator:
    def __init__(
        self,
        query: Type[Object],
        mutation: Optional[Type[Object]],
        scalars: List[Type[Scalar]],
        unions: Dict[FrozenSet[Type], str]
    ) -> None:
        self.py2gql_types = make_scalar_map(scalars)
        self.type_map: Dict[Type, GraphQLNamedType] = {}
        self.query = query
        self.mutation = mutation
        self.unions = unions

    def build(self) -> GraphQLSchema:
        query = self.map_type(self.query)
        mutation = self.map_type(self.mutation) if self.mutation else None
        # Interface implementations may not have been explicitly referenced in
        # the schema. But their interface must have been--so we want to
        # traverse all interfaces, find their subclasses and explicitly supply
        # them to the schema.
        #
        # To traverse all instances, we hackily construct a temporary schema,
        # then check self.type_map to see what the schema found.
        tmp_schema = GraphQLSchema(
            query=query,
            mutation=mutation,
        )
        extra_types = []
        for interface in list(self.type_map):
            if isinstance(interface, type) and issubclass(interface, Interface):
                for impl in interface.__subclasses__():
                    ann = types.AClass(None, impl)
                    extra_types.append(self.translate_type_inner(ann))
        return GraphQLSchema(
            query=query,
            mutation=mutation,
            types=extra_types
        )


    def translate_type(self, ann: types.Annotation) -> GraphQLNamedType:
        if ann.t in self.type_map:
            return self.type_map[ann.t]
        gt = self._translate_type_impl(ann)
        self.type_map[ann.t] = gt
        return gt

    def translate_type_inner(self, ann: types.Annotation) -> GraphQLNamedType:
        return self.translate_type(ann).of_type

    def _translate_type_impl(self, ann: types.Annotation) -> GraphQLNamedType:
        if isinstance(ann, types.AList):
            return GraphQLNonNull(GraphQLList(
                self.translate_type(ann.of_type)
            ))
        elif isinstance(ann, types.AOptional):
            return self.translate_type_inner(ann.of_type)
        elif isinstance(ann, types.AUnion):
            return GraphQLNonNull(self.map_union(ann))
        elif isinstance(ann, types.ANewType):
            return GraphQLNonNull(self.map_newtype(ann))
        assert isinstance(ann, types.AClass)
        t = ann.t
        if issubclass(t, Object):
            return GraphQLNonNull(self.map_type(t))
        elif issubclass(t, Interface):
            return GraphQLNonNull(self.map_interface(t))
        elif dataclasses.is_dataclass(t):
            return GraphQLNonNull(self.map_input(t))
        elif issubclass(t, enum.Enum):
            return GraphQLNonNull(self.map_enum(t))
        elif t in BUILTIN_SCALARS:
            return GraphQLNonNull(BUILTIN_SCALARS[t])
        elif t in self.py2gql_types:
            return GraphQLNonNull(self.py2gql_types[t])
        raise NotImplementedError(f"""Cannot translate {t}. Suggestions:
        - Did you forget to add its scalar mapper to the `scalars` list?""")

    def map_type(self, cls: Type) -> GraphQLObjectType:
        interfaces = [
            types.AClass(None, t) for t in cls.__mro__
            if issubclass(t, Interface) and t != cls and t != Interface
        ]
        return GraphQLObjectType(
            name=cls.__name__,
            description=cls.__doc__,
            fields=lambda: self.map_fields(cls),
            interfaces=lambda: [self.translate_type_inner(t) for t in interfaces],
            is_type_of=lambda obj, info: isinstance(obj, cls)
        )

    def map_enum(self, cls: Type[enum.Enum]) -> GraphQLEnumType:
        return WorkingEnumType(cls)

    def map_interface(self, cls: Type[Interface]) -> GraphQLInterfaceType:
        return GraphQLInterfaceType(
            name=cls.__name__,
            description=cls.__doc__,
            fields=lambda: self.map_fields(cls),
        )

    def map_input(self, cls: Type) -> GraphQLInputObjectType:
        return GraphQLInputObjectType(
            name=cls.__name__,
            description=cls.__doc__,
            fields=lambda: self.map_input_fields(cls),
            container_type=lambda data: cls(**data) # type: ignore
        )

    def map_fields(self, cls: Type[Union[Object, Interface]]
    ) -> Dict[str, GraphQLField]:
        fields = {}
        hints = types.get_annotations(cls)
        for name in dir(cls):
            if name.startswith('_'):
                continue
            value = getattr(cls, name)
            # 'value' could be:
            # 1. a property
            # 2. a function
            # 3. a hardcoded value
            if hasattr(value, 'fget'):
                # property
                fields[name] = self.property_field(name, value)
            elif callable(value):
                fields[name] = self.function_field(name, value)
            else:
                if name in hints:
                    # explicitly annotated assignment; will be handled below
                    continue
                guessed_type = type(value)
                fields[name] = self.attribute_field(name, types.AClass(None, guessed_type))

        for name, typ in hints.items():
            if name.startswith('_'):
                continue
            fields[name] = self.attribute_field(name, typ)
        return fields

    def map_input_fields(self, cls: Type) -> Dict[str, GraphQLInputObjectField]:
        fields = {}
        for field in dataclasses.fields(cls):
            fields[field.name] = GraphQLInputObjectField(
                type=self.translate_type(types.make_annotation(None, field.type))
            )
        return fields

    def property_field(self, name: str, p: property) -> GraphQLField:
        return_type = types.get_annotations(p.fget)['return']
        return GraphQLField(
            self.translate_type(return_type),
            description=p.__doc__,
            resolver=self.property_resolver(name)
        )

    def attribute_field(self, name: str, t: types.Annotation) -> GraphQLField:
        return GraphQLField(
            self.translate_type(t),
            resolver=self.property_resolver(name)
        )

    def function_field(self, name: str, f: Callable) -> GraphQLField:
        hints = types.get_annotations(f)
        return_type = hints.pop('return')
        def resolver(self_: Any, info: ResolveInfo, **gql_args: Any) -> Any:
            py_args = {}
            for name, value in gql_args.items():
                py_args[name] = value
            return f(self_, **py_args)
        return GraphQLField(
            self.translate_type(return_type),
            args={
                name:
                GraphQLArgument(type=self.translate_type(t))
                for name, t in hints.items()},
            description=f.__doc__,
            resolver=resolver
        )

    def map_newtype(self, t: types.ANewType) -> GraphQLNamedType:
        of_class = t.of_type.t
        if of_class in BUILTIN_SCALARS:
            return self.map_custom_scalar(
                t.typename,
                BUILTIN_SCALARS[of_class]
            )
        elif of_class in self.py2gql_types:
            return self.map_custom_scalar(
                t.typename,
                self.py2gql_types[of_class]
            )
        else:
            # just de-alias the newtype I guess
            return self.translate_type(t.of_type)

    def map_custom_scalar(self, name: str, supertype: GraphQLScalarType
    ) -> GraphQLScalarType:
        return GraphQLScalarType(
            name=name,
            serialize=supertype.serialize,
            parse_literal=supertype.parse_literal,
            parse_value=supertype.parse_value,
        )

    def map_union(self, ann: types.AUnion) -> GraphQLUnionType:
        args = [of_t.t for of_t in ann.of_types]
        name = self.unions.get(frozenset(args))
        if name is None:
            raise ValueError(f"""Could not find a name for Union[{args}].

            In GraphQL, any union needs a name--please use the `unions`
            argument to `make_schema` to supply one.""")
        return GraphQLUnionType(
            name=name,
            # translate_type returns a NonNull, but we need the underlying for
            # our union
            types=[self.translate_type_inner(ann) for ann in ann.of_types],
        )

    def property_resolver(self, name: str) -> Callable:
        return lambda self, info: getattr(self, name)

def make_schema(
    query: Type[Object],
    mutation: Optional[Type[Object]] = None,
    scalars: List[Type[Scalar]] = None,
    unions: Dict[str, Type] = None
) -> GraphQLSchema:
    if unions is None:
        unions = {}
    unions_inverted = {frozenset(t.__args__): name for name, t in unions.items()}
    return SchemaCreator(query, mutation, scalars or [], unions_inverted).build()
