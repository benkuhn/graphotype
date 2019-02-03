from typing import Mapping

from .schema_types import TypeRef

# Types that have different Python names than their GQL names
DEFAULT_RENAMES: Mapping[str, str] = {
    'Int': 'int',
    'String': 'str',
    'Boolean': 'bool',
    'Float': 'float',
    'Bytes': 'bytes',
}

class TemplateFilters:
    def __init__(self, renames: Mapping[str, str]) -> None:
        self.pytype_mapping = {**DEFAULT_RENAMES, **renames}

    def pytype(self, t: TypeRef, nonnull=False) -> str:
        """Render a TypeRef into a string"""

        of_type = t.get("ofType")
        if t["kind"] == 'NON_NULL':
            # Unwrap the nonnull
            assert of_type
            return self.pytype(of_type, nonnull=True)

        if t["kind"] == 'LIST':
            # Wrap 'List[]' around the recursive
            assert of_type
            inner = self.pytype(of_type, nonnull=True)
            return f'List[{inner}]'

        name = t["name"]
        assert name  # TODO(ben) is this valid?
        if name in self.pytype_mapping:
            mapped = self.pytype_mapping[name]
        else:
            mapped = name

        if not nonnull:
            mapped = f'Optional[{mapped}]'

        return mapped

    def quoted(self, s: str) -> str:
        """Return a quoted s (for Python source code)"""
        return repr(s)
