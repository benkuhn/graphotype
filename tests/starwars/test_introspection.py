import pytest

from graphql import graphql
from graphql.error import format_error
from graphql.pyutils.contain_subset import contain_subset

def assert_contain_subset(expected, actual):
    obj = (dict, list, tuple)
    # type: (Any, Any) -> bool
    t_actual = type(actual)
    t_expected = type(expected)
    actual_is_dict = issubclass(t_actual, dict)
    expected_is_dict = issubclass(t_expected, dict)
    both_dicts = actual_is_dict and expected_is_dict
    if not (both_dicts):
        assert issubclass(t_actual, t_expected) or issubclass(t_expected, t_actual)
    if not isinstance(expected, obj) or expected is None:
        assert expected == actual
    assert not (expected and not actual)
    if isinstance(expected, list):
        aa = actual[:]
        for exp in expected:
            if not any([contain_subset(exp, act) for act in aa]):
                raise AssertionError(f"{exp} not found in {aa}")
        return
    for key in expected.keys():  # type: ignore
        eo = expected[key]
        ao = actual.get(key)
        if isinstance(eo, obj) and eo is not None and ao is not None:
            assert_contain_subset(eo, ao)
        else:
            assert ao == eo

def test_allows_querying_the_schema_for_types(schema):
    query = """
        query IntrospectionTypeQuery {
          __schema {
            types {
              name
            }
          }
        }
    """
    expected = {
        "__schema": {
            "types": [
                {"name": "Query"},
                {"name": "Episode"},
                {"name": "Character"},
                {"name": "String"},
                {"name": "Human"},
                {"name": "Droid"},
                {"name": "__Schema"},
                {"name": "__Type"},
                {"name": "__TypeKind"},
                {"name": "Boolean"},
                {"name": "__Field"},
                {"name": "__InputValue"},
                {"name": "__EnumValue"},
                {"name": "__Directive"},
                {"name": "__DirectiveLocation"},
            ]
        }
    }

    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)


def test_allows_querying_the_schema_for_query_type(schema):
    query = """
      query IntrospectionQueryTypeQuery {
        __schema {
          queryType {
            name
          }
        }
      }
    """

    expected = {"__schema": {"queryType": {"name": "Query"}}}
    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)


def test_allows_querying_the_schema_for_a_specific_type(schema):
    query = """
      query IntrospectionDroidTypeQuery {
        __type(name: "Droid") {
          name
        }
      }
    """

    expected = {"__type": {"name": "Droid"}}
    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)


def test_allows_querying_the_schema_for_an_object_kind(schema):
    query = """
      query IntrospectionDroidKindQuery {
        __type(name: "Droid") {
          name
          kind
        }
      }
    """

    expected = {"__type": {"name": "Droid", "kind": "OBJECT"}}
    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)


def test_allows_querying_the_schema_for_an_interface_kind(schema):
    query = """
      query IntrospectionCharacterKindQuery {
        __type(name: "Character") {
          name
          kind
        }
      }
    """
    expected = {"__type": {"name": "Character", "kind": "INTERFACE"}}
    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)


def test_allows_querying_the_schema_for_object_fields(schema):
    query = """
      query IntrospectionDroidFieldsQuery {
        __type(name: "Droid") {
          name
          fields {
            name
            type {
              name
              kind
            }
          }
        }
      }
    """

    expected = {
        "__type": {
            "name": "Droid",
            "fields": [
                {"name": "id", "type": {"name": None, "kind": "NON_NULL"}},
                {"name": "name", "type": {"name": "String", "kind": "SCALAR"}},
                {"name": "friends", "type": {"name": None, "kind": "LIST"}},
                {"name": "appearsIn", "type": {"name": None, "kind": "LIST"}},
                {
                    "name": "primaryFunction",
                    "type": {"name": "String", "kind": "SCALAR"},
                },
            ],
        }
    }

    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)


def test_allows_querying_the_schema_for_nested_object_fields(schema):
    query = """
      query IntrospectionDroidNestedFieldsQuery {
        __type(name: "Droid") {
          name
          fields {
            name
            type {
              name
              kind
              ofType {
                name
                kind
              }
            }
          }
        }
      }
    """

    expected = {
        "__type": {
            "name": "Droid",
            "fields": [
                {
                    "name": "id",
                    "type": {
                        "name": None,
                        "kind": "NON_NULL",
                        "ofType": {"name": "String", "kind": "SCALAR"},
                    },
                },
                {
                    "name": "name",
                    "type": {"name": "String", "kind": "SCALAR", "ofType": None},
                },
                {
                    "name": "friends",
                    "type": {
                        "name": None,
                        "kind": "LIST",
                        "ofType": {"name": "Character", "kind": "INTERFACE"},
                    },
                },
                {
                    "name": "appearsIn",
                    "type": {
                        "name": None,
                        "kind": "LIST",
                        "ofType": {"name": "Episode", "kind": "ENUM"},
                    },
                },
                {
                    "name": "primaryFunction",
                    "type": {"name": "String", "kind": "SCALAR", "ofType": None},
                },
            ],
        }
    }
    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)

@pytest.mark.xfail
def test_allows_querying_the_schema_for_field_args(schema):
    query = """
      query IntrospectionQueryTypeQuery {
        __schema {
          queryType {
            fields {
              name
              args {
                name
                description
                type {
                  name
                  kind
                  ofType {
                    name
                    kind
                  }
                }
                defaultValue
              }
            }
          }
        }
      }
    """

    expected = {
        "__schema": {
            "queryType": {
                "fields": [
                    {
                        "name": "hero",
                        "args": [
                            {
                                "defaultValue": None,
                                "description": "If omitted, returns the hero of the whole "
                                + "saga. If provided, returns the hero of "
                                + "that particular episode.",
                                "name": "episode",
                                "type": {
                                    "kind": "ENUM",
                                    "name": "Episode",
                                    "ofType": None,
                                },
                            }
                        ],
                    },
                    {
                        "name": "human",
                        "args": [
                            {
                                "name": "id",
                                "description": "id of the human",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {"kind": "SCALAR", "name": "String"},
                                },
                                "defaultValue": None,
                            }
                        ],
                    },
                    {
                        "name": "droid",
                        "args": [
                            {
                                "name": "id",
                                "description": "id of the droid",
                                "type": {
                                    "kind": "NON_NULL",
                                    "name": None,
                                    "ofType": {"kind": "SCALAR", "name": "String"},
                                },
                                "defaultValue": None,
                            }
                        ],
                    },
                ]
            }
        }
    }

    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)


def test_allows_querying_the_schema_for_documentation(schema):
    query = """
      query IntrospectionDroidDescriptionQuery {
        __type(name: "Droid") {
          name
          description
        }
      }
    """

    expected = {
        "__type": {
            "name": "Droid",
            "description": "A mechanical creature in the Star Wars universe.",
        }
    }
    result = graphql(schema, query)
    assert not result.errors
    assert_contain_subset(result.data, expected)
