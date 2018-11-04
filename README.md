# BetterGQL: Typed GQL server library

## TODO

- [x] Execution basically works
- [x] Enums
- [x] Lists
- [ ] IDs
- [ ] Optionals
- [ ] Unions
- [ ] Custom scalars
- [ ] Interfaces
- [ ] Input objects
- [ ] Query factory

## Overview

Define your GraphQL schema in Python3.5+ code using classes and type annotations.

This library is intended as a replacement for [Graphene](https://graphene-python.org/). However, bettergql (like graphene) depends on [graphql-core](https://github.com/graphql-python/graphql-core).

We recommend use of [mypy](http://mypy-lang.blogspot.com/) alongside this
library. With appropriate type annotations, mypy will check that your
implementation satisfies the schema that you define, which rules out large
classes of programming errors when implementing your schema.

Example:
```py
import main
import graphql

class Query(main.GQLObject):
    def c(self, d: bool, e: float) -> 'Foo':
        return Foo(7 if d else int(e), str(d))

class Foo(main.GQLObject):
    def __init__(self, a: int, b: str) -> None:
        self.a = a
        self.b = b
    a: int
    b = 'foo'


schema = main.make_schema(query=Query, mutation=None)

print(graphql.print_schema(schema))
```
prints:
```
schema {
  query: Query
}

type Foo {
  b: String
  a: Int
}

type Query {
  c(d: Boolean, e: Float): Foo
}
```

### Scalar Types
- The usual Python types (int, str, bool, float) are mapped to the corresponding usual GraphQL types.
- To get the `ID` GraphQL type, import it from this package. ID is defined as a NewType of str.
- Enums must extend from the Python standard library enum.Enum. The Python names are exposed as the elements of the schema enum. The values are not exposed in the schema.
- Custom scalar types are serialized/deserialized using supplemental classes provided at schema creation time. To support scalar type T in your Python schema, supply a class which implements the Scalar[T] protocol (i.e., expose `parse` and `serialize` as classmethods). The GraphQL schema will be created with a custom scalar type whose name is `T.__name__`.

### Composite Types
- Interfaces are defined as Python classes which derive from bettergql.GQLInterface, either directly or indirectly via other interfaces.
- Object types are defined as Python classes which derive from bettergql.GQLObject, plus zero or more interfaces.
- Input objects are defined as Python dataclasses (must be annotated with @dataclass).
- Unions are defined using `typing.Union[...]` 

Interfaces and unions are discriminated at runtime where necessary using isinstance checks.

### What types are included?

In order to determine the set of types which are part of the schema, we recursively traverse all types referenced by the root Query or Mutation types provided to `create_schema` and add all thus-discovered types to the schema.

Additionally, we recursively search for subclasses of all Interfaces thus discovered and add them to the schema as well. (Why? You might create a class hierarchy of, say, an Animal interface, Dog(Animal) and Cat(Animal); we assume that if you created Dog and Cat, you might want to return them someday wherever Animal is currently part of the interface, even if Dog/Cat are not separately referenced.)

### Separation of Concerns

Better-GQL allows you to define your schema separately from the implementation of resolvers and mutators. This is the recommended way to write your code.

Why? It's easy to see and modify your schema all in one place; it's tougher to accidentally make breaking API changes; you don't have to import your whole implementation in order to introspect the schema; and you can include implementation-detail fields in your implementation code that aren't part of the schema.

Of course, you are welcome to write implementation code wherever you feel like it. But if you want to separate your concerns, you just need to specify the root Query and Mutation class implementations by calling `implement_schema`. These subclasses should descend from your Query and Mutation classes in the schema definition.

