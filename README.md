# graphotype

*A concise, type-safe way to write GraphQL backends in Python.*

## Overview

Define your GraphQL schema in Python3.6+ code using classes and type annotations.

Graphotype is intended as a replacement for [Graphene](https://graphene-python.org/). However, graphotype (like graphene) depends on [graphql-core](https://github.com/graphql-python/graphql-core).

We highly recommend use of [mypy](http://mypy-lang.blogspot.com/) alongside this
library. Using the type annotations you write for your schema, mypy can check that your
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
- To get the `ID` GraphQL type, import it from this package. ID is defined as a [`typing.NewType`](https://docs.python.org/3/library/typing.html#newtype) of str.
- In fact, any `typing.NewType` of a known scalar type can be used: we'll automatically derive serialize and deserialize functions for your NewType according to the underlying type, and define a distinct scalar type in your schema.
- Enums must extend from the Python standard library [enum.Enum](https://docs.python.org/3/library/enum.html). The Python names are exposed as the elements of the schema enum. The values are not exposed in the schema.
- Custom scalar types are serialized/deserialized using supplemental classes provided at schema creation time. To support scalar type T in your Python schema, supply a class which implements the Scalar[T] protocol (i.e., expose `parse` and `serialize` as classmethods). The GraphQL schema will be created with a custom scalar type whose name is `T.__name__`.

### Composite Types

- Lists are defined via `typing.List`.
- Optional values are defined via `typing.Optional`. All values not marked optional are marked as required in the schema. We recommend using Optional types liberally, as that's how GraphQL recommends you do it.
- Interfaces are defined as Python classes which derive from `graphotype.Interface`, either directly or indirectly via other interfaces.
- Object types are defined as Python classes which derive from `graphotype.Object`, plus zero or more interfaces.
- Input objects are defined as Python [dataclasses](https://docs.python.org/3/library/dataclasses.html) (must be annotated with @dataclass).
- Unions are defined using `EitherAB = typing.Union[A, B]`. 
  - Unions must be referenced by name, which means using strings ("forward references") in your type annotations when referencing a union. 
    For example, if `EitherAB` is a Union, you must use `MaybeAB = Optional['EitherAB']` instead of `MaybeAB = Optional[EitherAB]`.
  - *Note:* If you use Python 3.7+ with `from __future__ import annotations` at the top of your file, this restriction is lifted (because all annotations are interpreted as strings anyway). See `tests/test_unions.py` for examples.

Under the hood, the options for interfaces and unions are discriminated at runtime where necessary using `isinstance` checks.

### What types are included?

In order to determine the set of types which are part of the schema, we recursively traverse all types referenced by the root Query or Mutation types provided to `make_schema` and add all thus-discovered types to the schema.

Additionally, we recursively search for subclasses of all `Interface`s thus discovered and add them to the schema as well. (Why? You might create a class hierarchy of, say, an Animal interface, Dog(Animal) and Cat(Animal); we assume that if you created Dog and Cat, you might want to return them someday wherever Animal is currently part of the interface, even if Dog/Cat are not separately referenced.)

# More Examples

<table>
<tr>
    <th>Graphene</th><th>Graphotype</th>
</tr>
<tr>
<td>
<pre lang="python">
class Query(graphene.ObjectType):
    hello = graphene.String(
        description='A typical hello world'
    )
    def resolve_hello(self, info):
        return 'World'
</pre>
</td>
<td>
<pre lang="python">
class Query(graphotype.Object):
    def hello(self) -> str:
        """A typical hello world"""
        return 'World'
</pre>
</td>
</tr>

<tr>
<td>
<pre lang="python">
class Query(graphene.ObjectType):
    hello = graphene.String(
        argument=graphene.String(
            default_value="stranger"
        )
    )
    def resolve_hello(self, info, argument):
        return 'Hello ' + argument
</pre>

Here, Graphene requires you both specify `hello`'s type and write its resolver.

</td>
<td>
<pre lang="python">
class Query(graphotype.Object):
    def hello(
        self, 
        argument: str = "stranger"
    ) -> str:
        return 'Hello ' + argument
</pre>

With Graphotype, the definitions are one and the same.

</td>
</tr>

<tr>
<td>
<pre lang="python">
class Person(graphene.ObjectType):
    first_name = graphene.String()
    last_name = graphene.String()
    full_name = graphene.String()
    def resolve_full_name(self, info):
        return '{} {}'.format(
            self.first_name, self.last_name
        )
</pre>
</td>
<td>
<pre lang="python">
@dataclass
class Person(graphotype.Object):
    first_name: str
    last_name: str
    def full_name(self) -> str:
        return '{} {}'.format(
            self.first_name, self.last_name
        )
</pre>
Note for this example: Graphotype does not assume anything in particular about
how to construct any composite types other than input objects (which must be dataclasses). 
If you just inherit from `graphotype.Object` you don't inherit any constructor;
you can define it yourself if you like, or use dataclasses for everything (which we recommend).
</td>
</tr>
</table>


# Import an existing schema

If you already have a GraphQL schema you want to work with, it's easy to get started with Graphotype. 
After installing graphotype, you also need to `pip install jinja2 black`, then do

```bash
python -m graphotype import [schema_file]
```

This works with either .graphql schema format or a JSON introspection-query result, and outputs a Python file for you. 
See the `--help` of that command for more info.


# Development on Graphotype itself

To run the unit tests (requires python 3.7):
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e .
pytest
```
