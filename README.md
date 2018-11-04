# BetterGQL: Typed GQL server library

## TODO

- [ ] Lists
- [ ] Optionals
- [ ] Unions
- [ ] Custom scalars
- [ ] Interfaces

## Overview

Define your GraphQL schema in Python3.5+ code using classes and type annotations.

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


