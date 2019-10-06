from graphql import get_default_backend


def execute(schema, graphql_str):
    backend = get_default_backend()
    document = backend.document_from_string(schema, graphql_str)
    result = document.execute()
    if result.errors:
        raise result.errors[0]
    return result.data
