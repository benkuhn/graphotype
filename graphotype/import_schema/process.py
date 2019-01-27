from typing import IO, Any, Mapping
import pathlib

import jinja2

from .template_filters import TemplateFilters
from .schema_types import SchemaType

import_schema_folder = pathlib.Path(__file__).parent


def process(json_schema: Any, renames: Mapping[str, str] = {}) -> str:
    """Consume json_schema and produce rendered python file in Graphotype format"""
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(import_schema_folder / 'templates'))
    )

    env.filters['pytype'] = TemplateFilters(renames).pytype

    schema = json_schema["__schema"]

    topoffile = env.get_template("top_of_file.py.tmpl")
    out = topoffile.render()

    t: SchemaType
    for t in schema['types']:

        if t['name'].startswith('__'):
            # skip internal types
            continue

        kind = t['kind']

        if kind == 'OBJECT':
            tmpl = env.get_template("object_type.py.tmpl")
            out += tmpl.render(t=t)

        elif kind == 'INPUT_OBJECT':
            tmpl = env.get_template("input_object_type.py.tmpl")
            out += tmpl.render(t=t)

        elif kind == 'INTERFACE':
            tmpl = env.get_template("interface_type.py.tmpl")
            out += tmpl.render(t=t)

        elif kind == 'UNION':
            tmpl = env.get_template("union_type.py.tmpl")
            out += tmpl.render(t=t)

    return out

