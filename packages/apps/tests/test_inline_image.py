"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import time

from microsoft_teams.apps.files.inline_image import (
    AMS_IMAGE_ITEMTYPE,
    format_from_hint,
    inline_image_id,
    parse_inline_image_hints,
    sniff_image_format,
)


def test_sniff_recognizes_gif87a_as_well_as_gif89a() -> None:
    assert sniff_image_format(b"GIF87a") == "gif"


def test_sniff_does_not_treat_a_riff_container_other_than_webp_as_webp() -> None:
    wav = b"RIFF\x00\x00\x00\x00WAVE"

    assert sniff_image_format(wav) is None


def test_sniff_does_not_match_a_signature_longer_than_the_bytes() -> None:
    assert sniff_image_format(b"\x89PN") is None
    assert sniff_image_format(b"RIFF") is None
    assert sniff_image_format(b"") is None


def test_format_from_hint_accepts_jpg_and_any_case_and_rejects_an_unknown_name() -> None:
    assert format_from_hint("JPG") == "jpeg"
    assert format_from_hint(" Png ") == "png"
    assert format_from_hint("bmp") is None
    assert format_from_hint(None) is None


def test_inline_image_id_reads_the_id_only_from_an_inline_image_location() -> None:
    assert (
        inline_image_id("https://smba.trafficmanager.net/amer/v3/attachments/0-wus-d1-abc/views/original")
        == "0-wus-d1-abc"
    )
    assert inline_image_id("https://smba.trafficmanager.net/amer/v3/attachments/0-wus-d1-abc/views/thumbnail") is None


def test_inline_image_id_rejects_an_id_that_could_carry_a_path_separator_into_the_file_name() -> None:
    assert inline_image_id("https://smba.trafficmanager.net/amer/v3/attachments/a\\..\\..\\evil/views/original") is None
    assert inline_image_id("https://smba.trafficmanager.net/amer/v3/attachments/a%5C..%5Cevil/views/original") is None


def test_inline_image_id_reads_the_id_only_from_the_path_not_from_a_query_string_or_fragment() -> None:
    assert (
        inline_image_id(
            "https://smba.trafficmanager.net/amer/v3/conversations/x/members?x=/v3/attachments/a/views/original"
        )
        is None
    )
    assert (
        inline_image_id(
            "https://smba.trafficmanager.net/amer/v3/conversations/x/members#/v3/attachments/a/views/original"
        )
        is None
    )
    assert inline_image_id("https://smba.trafficmanager.net/amer/v3/attachments/a/views/original?x=1") == "a"


def test_hints_read_double_quoted_single_quoted_and_mixed_attribute_values() -> None:
    assert parse_inline_image_hints(f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="png" itemid="a">') == {"a": "png"}
    assert parse_inline_image_hints(f"<img itemtype='{AMS_IMAGE_ITEMTYPE}' itemscope='png' itemid='a'>") == {"a": "png"}
    assert parse_inline_image_hints(f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope=\'png\' itemid="a">') == {
        "a": "png"
    }


def test_hints_do_not_read_an_attribute_from_inside_the_value_of_another_attribute() -> None:
    assert parse_inline_image_hints(
        f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="png" alt="a itemscope=\'gif\'" itemid="a">'
    ) == {"a": "png"}
    assert parse_inline_image_hints(
        f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="png" alt=\'a itemscope="gif"\' itemid="a">'
    ) == {"a": "png"}


def test_hints_read_a_tag_holding_a_long_run_of_name_characters_in_linear_time() -> None:
    started = time.monotonic()

    html = f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="png" itemid="a" {"x" * 50_000}>'
    assert parse_inline_image_hints(html) == {"a": "png"}
    assert time.monotonic() - started < 0.25


def test_hints_read_many_unclosed_or_unbalanced_tags_in_linear_time() -> None:
    started = time.monotonic()

    for shape in ("<img ", '<img "', "<img '", '<img a="x', '<img a="x" ', "<img a=\"' "):
        assert parse_inline_image_hints(shape * 20_000) == {}
    assert time.monotonic() - started < 0.25


def test_hints_read_a_tag_whose_quoted_value_holds_a_closing_angle_bracket() -> None:
    html = f'<img alt="1 > 0" src="a.png" itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="png" itemid="a">'

    assert parse_inline_image_hints(html) == {"a": "png"}


def test_hints_match_tag_and_attribute_names_in_any_case() -> None:
    assert parse_inline_image_hints(f'<IMG ITEMTYPE="{AMS_IMAGE_ITEMTYPE}" ItemScope="png" ITEMID="a">') == {"a": "png"}


def test_hints_map_each_inline_image_in_the_message_to_its_own_hint() -> None:
    html = (
        f'<p><img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="png" itemid="a"></p>'
        f'<p><img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="jpeg" itemid="b"></p>'
    )

    assert parse_inline_image_hints(html) == {"a": "png", "b": "jpeg"}


def test_hints_ignore_an_image_that_is_not_marked_as_an_inline_image() -> None:
    assert parse_inline_image_hints('<img itemtype="http://example.com/Other" itemscope="png" itemid="a">') == {}
    assert parse_inline_image_hints('<img src="https://example.com/a.png" itemscope="png" itemid="a">') == {}


def test_hints_read_nothing_from_an_unquoted_or_bare_attribute() -> None:
    assert parse_inline_image_hints(f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope=png itemid="a">') == {}
    assert parse_inline_image_hints(f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope itemid="a">') == {}


def test_hints_do_not_decode_character_references() -> None:
    encoded = parse_inline_image_hints(f'<img itemtype="{AMS_IMAGE_ITEMTYPE}" itemscope="p&#110;g" itemid="a">')

    assert encoded == {"a": "p&#110;g"}
    assert format_from_hint(encoded["a"]) is None
    assert (
        parse_inline_image_hints(
            '<img itemtype="http:&#x2F;&#x2F;schema.skype.com/AMSImage" itemscope="png" itemid="a">'
        )
        == {}
    )
