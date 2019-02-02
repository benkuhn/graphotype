from typing import Optional, Union, List

from graphotype.types import make_annotation, AClass, AOptional, NoneType, AUnion, AList


def test_make_annotation_simple():
    assert make_annotation(None, str) == AClass(None, str)
    assert make_annotation(None, Optional[int]) == AOptional(
        None, Union[int, NoneType], of_type=AClass(None, int)
    )


def test_make_annotation_simple_named():
    assert make_annotation("str", str) == AClass("str", str)
    assert make_annotation("MaybeInt", Optional[int]) == AOptional(
        "MaybeInt", Union[int, NoneType], of_type=AClass(None, int)
    )


def test_make_annotation_unwraps_optional_and_list():
    """make_annotation will unwrap the brackets and preserve the 'raw' of whatever is inside
    your Optionals and Lists"""
    assert make_annotation("Optional[int]", Optional[int]) == AOptional(
        "Optional[int]", Union[int, NoneType], of_type=AClass("int", int)
    )
    assert make_annotation("List[int]", List[int]) == AList(
        "List[int]", List[int], of_type=AClass("int", int)
    )
    assert make_annotation("Optional[List[int]]", Optional[List[int]]) == AOptional(
        "Optional[List[int]]",
        Union[List[int], NoneType],
        of_type=AList("List[int]", List[int], of_type=AClass("int", int)),
    )


def test_make_annotation_union():
    """You can always call make_annotation on a Union, even though you
    might not be able to use it directly in a graphql type."""
    assert make_annotation(None, Union[str, int]) == AUnion(
        None, Union[str, int], of_types=[AClass(None, str), AClass(None, int)]
    )


def test_make_annotation_union_named():
    """The union name is preserved at the top level."""
    assert make_annotation("StrOrInt", Union[str, int]) == AUnion(
        "StrOrInt", Union[str, int], of_types=[AClass(None, str), AClass(None, int)]
    )


def test_make_annotation_opt_union():
    """make_annotation on unnamed optional Union works too"""
    assert make_annotation(None, Optional[Union[str, int]]) == AOptional(
        None,
        Optional[Union[str, int]],
        of_type=AUnion(
            None, Union[str, int], of_types=[AClass(None, str), AClass(None, int)]
        ),
    )


def test_make_annotation_opt_union_named():
    """make_annotation on optional named Union"""
    assert make_annotation('Optional[StrOrInt]', Optional[Union[str, int]]) == AOptional(
        'Optional[StrOrInt]',
        Optional[Union[str, int]],
        of_type=AUnion(
            'StrOrInt', Union[str, int], of_types=[AClass(None, str), AClass(None, int)]
        ),
    )



def test_make_annotation_list_union_named():
    """make_annotation on a list of named Union"""
    assert make_annotation("List[StrOrInt]", List[Union[str, int]]) == (
        AList(
            "List[StrOrInt]",
            List[Union[str, int]],
            of_type=AUnion(
                "StrOrInt",
                Union[str, int],
                of_types=[AClass(None, str), AClass(None, int)],
            ),
        )
    )
