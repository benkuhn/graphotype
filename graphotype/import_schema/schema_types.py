from __future__ import annotations

from typing import Optional, List

from mypy_extensions import TypedDict

TypeRef = TypedDict('TypeRef',
                    {
                        'kind': str,  # NON_NULL / LIST / SCALAR
                        'name': Optional[str],
                        'ofType': Optional['TypeRef']
                    })

Field = TypedDict('Field',
                  {
                      'name': str,
                      'description': Optional[str],
                      'args': List['Argument'],
                      'type': TypeRef,
                      'isDeprecated': bool,
                      'deprecationReason': Optional[str],
                  })

Arg = TypedDict('Arg',
                {
                    'name': str,
                    'description': Optional[str],
                    'type': TypeRef,
                    'defaultValue': Optional[str],  # This is a gql literal (!) i think
                })

SchemaType = TypedDict('SchemaType',
                       {
                           'kind': str,
                           'name': str,
                           'description': Optional[str],
                           'fields': Optional[List[Field]],
                           'inputFields': Optional[List[Arg]],
                           'interfaces': Optional[List['x']],
                           'enumValues': Optional[List['y']],
                           'possibleTypes': Optional[List[TypeRef]],
                       })
