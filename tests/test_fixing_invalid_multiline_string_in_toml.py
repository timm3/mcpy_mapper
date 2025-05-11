import pytest


@pytest.mark.parametrize(
    "toml,error_message,expected_result",
    [
        (
            """invalidMultilineString = "Oh\nno!\"""",
            "Illegal character '\\n' (at line 1, column 29)",
            """invalidMultilineString = "Oh no!\"""",
        ),
    ],
)
def test_fix_single_invalid_multiline_string(
    toml: str, error_message: str, expected_result: str
):
    from mcpy_mapper.local_crawler import _fix_invalid_multiline_string

    result = _fix_invalid_multiline_string(toml, error_message)
    assert result == expected_result
