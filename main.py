from collections import OrderedDict
import enum
import functools
from typing import (
    Type, get_type_hints, Generic, List, Dict, TypeVar, Any, Callable,
    GenericMeta
)

from graphql import (
    graphql,
    GraphQLSchema,
    GraphQLObjectType,
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
)
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
    def __init__(self, scalars: List[Type[Scalar]]) -> None:
        self.py2gql_types = make_scalar_map(scalars)

    @functools.lru_cache(maxsize=None)
    def map_type(self, cls: Type[GQLObject]) -> GraphQLObjectType:
        return GraphQLObjectType(
            name=cls.__name__,
            description=cls.__doc__,
            fields=lambda: self.map_fields(cls)
        )

    @functools.lru_cache(maxsize=None)
    def map_enum(self, cls: Type[enum.Enum]) -> GraphQLEnumType:
        return WorkingEnumType(cls)

    def map_fields(self, cls: Type[GQLObject]) -> Dict[str, GraphQLField]:
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

    def translate_type(self, t: Type) -> GraphQLObjectType:
        if issubclass(t, GQLObject):
            return self.map_type(t)
        elif isinstance(t, GenericMeta):
            origin = t.__origin__
            if origin == List:
                [of_type] = t.__args__
                return GraphQLList(
                    self.translate_type(of_type)
                )
        elif issubclass(t, enum.Enum):
            return self.map_enum(t)
        elif t in BUILTIN_SCALARS:
            return BUILTIN_SCALARS[t]
        elif t in self.py2gql_types:
            return self.py2gql_types[t]
        raise NotImplementedError(f"Cannot translate {t}")

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
    scalars: List[Type[Scalar]] = None
) -> GraphQLSchema:
    sc = SchemaCreator(scalars or [])
    return GraphQLSchema(
        query=sc.map_type(query),
        mutation=sc.map_type(mutation) if mutation else None,
    )
