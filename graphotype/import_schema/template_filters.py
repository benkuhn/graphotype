from typing import Mapping

from .schema_types import TypeRef

# Types that have different Python names than their GQL names
pytype_mapping: Mapping[str, str] = {
    'Int': 'int',
    'String': 'str',
    'Boolean': 'bool',
    'Float': 'float',
    'Bytes': 'bytes',
}

def pytype(t: TypeRef, nonnull=False) -> str:
    """Render a TypeRef into a string"""

    if t["kind"] == 'NON_NULL':
        # Unwrap the nonnull
        return pytype(t["ofType"], nonnull=True)

    if t["kind"] == 'LIST':
        # Wrap 'List[]' around the recursive
        inner = pytype(t["ofType"], nonnull=True)
        return f'List[{inner}]'

    name = t["name"]
    if name in pytype_mapping:
        mapped = pytype_mapping[name]
    else:
        mapped = name

    if not nonnull:
        mapped = f'Optional[{mapped}]'

    return mapped
