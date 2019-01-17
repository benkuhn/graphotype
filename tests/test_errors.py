import pytest

from graphotype import make_schema, SchemaError

def test_no_inherit_object():
    class Query:
        i = 1

    with pytest.raises(SchemaError) as e:
        make_schema(Query)
    assert "Did you forget to inherit Object?" in str(e.value)
