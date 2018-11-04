from collections import OrderedDict
import enum
import functools
from typing import (
    Type, get_type_hints, Generic, List, Dict, TypeVar, Any, Callable,
    GenericMeta, Union, _Union, NewType, Set, Optional
)

from graphql import (
    graphql,
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
    GraphQLUnionType
)
from graphql.type.definition import GraphQLNamedType
from graphql.language import ast

BUILTIN_SCALARS = {
    int: GraphQLInt,
    float: GraphQLFloat,
    str: GraphQLString,
    bool: GraphQLBoolean
}

T = TypeVar('T')
class Scalar(Generic[T]):
    t: Type[T]

    @classmethod
    def parse(cls, s: Any) -> T:
        raise NotImplementedError()

    @classmethod
    def serialize(cls, o: T) -> Any:
        raise NotImplementedError()

class GQLObject:
    pass

class GQLInterface:
    pass

def is_union(t: Type) -> bool:
    return isinstance(t, _Union)

def is_newtype(t: Type) -> bool:
    return hasattr(t, '__supertype__')

ID = NewType('ID', str)

class WorkingEnumType(GraphQLEnumType):
    def __init__(self, cls: Type[enum.Enum]):
        self.py_cls = cls
        super().__init__(
            name=cls.__name__,
            description=cls.__doc__,
            values=OrderedDict([
                (v.name, GraphQLEnumValue(v.value))
                for v in cls
            ])
        )

    def parse_literal(self, value_ast):
        value = super().parse_literal(value_ast)
        return self.py_cls(value)

    def parse_value(self, value):
        value = super().parse_value(value)
        return self.py_cls(value)

def ast_to_value(node):
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
        return {field.name: ast_to_value(field.value) for field in node.fields}
    # TODO handle enum values
    else:
        raise NotImplementedError()

def make_scalar_map(scalars: List[Type[Scalar]]) -> Dict[Type, GraphQLScalarType]:
    result = {}
    for scalar in scalars:
        result[scalar.t] = GraphQLScalarType(
            name=scalar.__name__,
            description=scalar.__doc__,
            serialize=scalar.serialize,
            parse_value=scalar.parse,
            parse_literal=lambda node: scalar.parse(ast_to_value(node))
        )
    return result

class SchemaCreator:
    def __init__(
        self,
        query: Type[GQLObject],
        mutation: Optional[Type[GQLObject]],
        scalars: List[Type[Scalar]],
    ) -> None:
        self.py2gql_types = make_scalar_map(scalars)
        self.type_map = {}
        self.query = query
        self.mutation = mutation

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
        for interface in self.type_map:
            if isinstance(interface, type) and issubclass(interface, GQLInterface):
                for impl in interface.__subclasses__():
                    extra_types.append(self.map_type(impl))
        return GraphQLSchema(
            query=query,
            mutation=mutation,
            types=extra_types
        )


    def translate_type(self, t: Type) -> GraphQLNamedType:
        if t in self.type_map:
            return self.type_map[t]
        gt = self._translate_type_impl(t)
        self.type_map[t] = gt
        return gt

    def translate_type_inner(self, t: Type) -> GraphQLNamedType:
        return self.translate_type(t).of_type

    def _translate_type_impl(self, t: Type) -> GraphQLNamedType:
        if isinstance(t, GenericMeta):
            origin = t.__origin__
            if origin == List:
                [of_type] = t.__args__
                return GraphQLNonNull(GraphQLList(
                    self.translate_type(of_type)
                ))
        elif is_union(t):
            return self.map_optional(t)
        elif is_newtype(t):
            return GraphQLNonNull(self.map_newtype(t))
        elif issubclass(t, GQLObject):
            return GraphQLNonNull(self.map_type(t))
        elif issubclass(t, GQLInterface):
            return GraphQLNonNull(self.map_interface(t))
        elif issubclass(t, enum.Enum):
            return GraphQLNonNull(self.map_enum(t))
        elif t in BUILTIN_SCALARS:
            return GraphQLNonNull(BUILTIN_SCALARS[t])
        elif t in self.py2gql_types:
            return GraphQLNonNull(self.py2gql_types[t])
        raise NotImplementedError(f"Cannot translate {t}")

    def map_type(self, cls: Type[GQLObject]) -> GraphQLObjectType:
        interfaces = [
            t for t in cls.__mro__
            if issubclass(t, GQLInterface) and t != cls and t != GQLInterface
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

    def map_interface(self, cls: Type[GQLInterface]) -> GraphQLInterfaceType:
        return GraphQLInterfaceType(
            name=cls.__name__,
            description=cls.__doc__,
            fields=lambda: self.map_fields(cls),
        )

    def map_fields(self, cls: Type[Union[GQLObject, GQLInterface]]
    ) -> Dict[str, GraphQLField]:
        fields = {}
        hints = get_type_hints(cls)
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
                fields[name] = self.attribute_field(name, guessed_type)

        for name, typ in hints.items():
            fields[name] = self.attribute_field(name, typ)
        return fields

    def property_field(self, name: str, p: property) -> GraphQLField:
        return_type: Type = get_type_hints(p.fget)['return']
        return GraphQLField(
            self.translate_type(return_type),
            description=p.__doc__,
            resolver=self.property_resolver(name, return_type)
        )

    def attribute_field(self, name: str, t: Type) -> GraphQLField:
        return GraphQLField(
            self.translate_type(t),
            resolver=self.property_resolver(name, t)
        )

    def function_field(self, name: str, f: Callable) -> GraphQLField:
        hints = get_type_hints(f)
        return_type: Type = hints.pop('return')
        def resolver(self_, info, **gql_args):
            py_args = {}
            for name, value in gql_args.items():
                py_args[name] = self.gql2py(hints[name], value)
            return self.py2gql(return_type, f(self_, **py_args))
        return GraphQLField(
            self.translate_type(return_type),
            args={
                name:
                GraphQLArgument(type=self.translate_type(t))
                for name, t in hints.items()},
            description=f.__doc__,
            resolver=resolver
        )

    def map_optional(self, t: _Union) -> GraphQLNamedType:
        NoneType = type(None)
        args = t.__args__
        if len(args) > 2 or NoneType not in args:
            raise ValueError("""Cannot translate type {t}.

            If you want a union you must name it via NewType.""")
        [t_inner] = [
            self.translate_type_inner(arg)
            for arg in args
            if arg != NoneType
        ]
        return t_inner

    def map_newtype(self, t: Any) -> GraphQLNamedType:
        if is_union(t.__supertype__):
            return self.map_union(t.__name__, t.__supertype__)
        elif t.__supertype__ in BUILTIN_SCALARS:
            return self.map_custom_scalar(
                t.__name__,
                BUILTIN_SCALARS[t.__supertype__]
            )
        else:
            # just de-alias the newtype I guess
            return translate_type(t.__supertype__)

    def map_custom_scalar(self, name: str, supertype: GraphQLScalarType
    ) -> GraphQLScalarType:
        return GraphQLScalarType(
            name=name,
            serialize=supertype.serialize,
            parse_literal=supertype.parse_literal,
            parse_value=supertype.parse_value,
        )

    def map_union(self, name: str, t: _Union) -> GraphQLUnionType:
        args = t.__args__
        return GraphQLUnionType(
            name=name,
            # translate_type returns a NonNull, but we need the underlying for
            # our union
            types=[self.translate_type_inner(t) for t in args],
        )

    def property_resolver(self, name: str, t: Type) -> Callable:
        def resolver(self, info):
            return getattr(self, name)
        return resolver

    def py2gql(self, pyt: Type, i: Any) -> Any:
        # TODO I think only enums need to be hacked around here, gql-core
        # does the rest
        #gqlt = self.py2gql_types[pyt]
        #return gqlt.serialize(i)
        return i

    def gql2py(self, pyt: Type, i: Any) -> Any:
        # TODO I think only enums need to be hacked around here, gql-core
        # does the rest
        #gqlt = self.py2gql_types[pyt]
        #return gqlt.parse_value(i)
        return i

def make_schema(
    query: Type[GQLObject],
    mutation: Type[GQLObject],
    scalars: List[Type[Scalar]] = None,
) -> GraphQLSchema:
    return SchemaCreator(query, mutation, scalars or []).build()
