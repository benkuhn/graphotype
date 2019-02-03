from typing import IO, List, Tuple

import argparse
import importlib

from graphql import GraphQLSchema, graphql, build_ast_schema, parse as gql_parse
from graphql.error.syntax_error import GraphQLSyntaxError
from graphql.utils.schema_printer import print_schema
from graphql.utils.introspection_query import introspection_query

def _schema_type(path: str) -> GraphQLSchema:
    # TODO validation
    modpath, varname = path.split(':')
    mod = importlib.import_module(modpath)
    var = getattr(mod, varname)
    if not isinstance(var, GraphQLSchema):
        raise ValueError(f"{path} is not an instance of GraphQLSchema")
    return var

def _add_schema_obj(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'schema',
        help='Path to Python schema object, e.g. `path.to.module:var`',
        type=_schema_type
    )

def _rename_type(s: str) -> Tuple[str, str]:
    lhs, rhs = s.split('=')
    return lhs, rhs


def dump(schema: GraphQLSchema, json: bool, pretty: bool, file: IO[str]) -> None:
    if json:
        import json as mjson
        data = graphql(schema, introspection_query).data
        mjson.dump(
            {'data': data}, file, indent=2 if pretty else None
        )
    else:
        file.write(print_schema(schema))

def serve(schema: GraphQLSchema, port: int) -> None:
    try:
        import flask
        from flask_graphql import GraphQLView
    except ImportError:
        raise ImportError('flask_graphql must be installed')
    app = flask.Flask('graphotype')
    app.add_url_rule('/', view_func=GraphQLView.as_view(
        'graphql', schema=schema, graphiql=True
    ))
    app.run(port=port)


def import_schema(
        input_schema: IO[str],
        output: IO[str],
        rename_type: List[Tuple[str, str]]
) -> None:
    """Import an existing json or graphql schema file, outputting a matching stub Graphotype file.

    If it's a json file, the correct format is: {"data": {"__schema": ...}}
    If a graphql file, the correct format is:   schema { query: ... }

    The output Python code is compatible with python 3.7. Unknown scalar and enum types
    will appear in the output unchanged by default. You can rename them with
       -r InputName=OutputName
    on the command line.
    """
    try:
        import jinja2
        import black
    except ImportError:
        raise ImportError('jinja2 and black must be installed')

    renames = dict(rename_type)

    import json

    source = input_schema.read()
    try:
        js_ast = json.loads(source)['data']
    except (json.JSONDecodeError, KeyError) :
        # let's try schema parsing
        try:
            gql_ast_schema = build_ast_schema(gql_parse(source))
            js_ast = graphql(gql_ast_schema, introspection_query).data
        except GraphQLSyntaxError as e:
            # Ok, that didn't work either -- throw it back to the user
            raise Exception("Please specify a valid JSON introspection or GraphQL schema file to import") from e

    from . import import_schema as mod
    result = mod.process(js_ast, renames)

    try:
        result = black.format_file_contents(result, line_length=80, fast=False)
    except black.NothingChanged:
        # this is ok, though surprising
        pass

    output.write(result)


def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser(
        description="Manipulate graphotype schemas."
    )
    subparsers = parser.add_subparsers(title='command')

    # dump command
    dump_parser = subparsers.add_parser('dump', help='Write schema to a file')
    _add_schema_obj(dump_parser)
    dump_parser.add_argument(
        'file',
        type=argparse.FileType('w'),
        help='The file to dump to'
    )
    dump_parser.add_argument(
        '-j',
        '--json',
        action='store_true',
        help='Write JSON instead of GQL syntax'
    )
    dump_parser.add_argument(
        '-p',
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output'
    )
    dump_parser.set_defaults(func=dump)

    # serve
    serve_parser = subparsers.add_parser('serve', help='Start a local GQL server')
    _add_schema_obj(serve_parser)
    serve_parser.add_argument('-p', '--port', type=int, default=8123)
    serve_parser.set_defaults(func=serve)

    # import
    import_parser = subparsers.add_parser('import', help='Import existing GQL schema and convert to Graphotype Python code')
    import_parser.add_argument(
        'input_schema',
        type=argparse.FileType('r'),
        help="The input schema (in graphql schema or json format)"
    )
    import_parser.add_argument('-o', '--output', type=argparse.FileType('w'), default=sys.stdout)
    import_parser.add_argument(
        '-r',
        '--rename-type',
        type=_rename_type,
        action='append',
        default=[],
        help="""Rename a scalar or enum type in output. (example: --rename-type Date=datetime)"""
    )
    import_parser.set_defaults(func=import_schema)

    parsed = parser.parse_args(argv)
    params = vars(parsed)
    func = params.pop('func')
    func(**params)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
