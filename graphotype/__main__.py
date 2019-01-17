from typing import List
from typing import IO

import argparse
import importlib
import os

from graphql import GraphQLSchema, graphql
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

    parsed = parser.parse_args(argv)
    params = vars(parsed)
    func = params.pop('func')
    func(**params)


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
