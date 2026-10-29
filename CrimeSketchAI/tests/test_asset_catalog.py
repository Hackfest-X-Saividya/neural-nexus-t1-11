"""
Unit tests for CrimeSketchAI Asset Catalog.

Validates the verified hairstyles, eyebrows, bald handling, natural language aliases,
and fragment resolution.
"""

import pytest
from backend.parser.asset_catalog import (
    HAIRSTYLE_CATALOG,
    EYEBROW_CATALOG,
    VERIFIED_ASSET_ALLOWLIST,
    find_hair_by_text,
    find_eyebrow_by_text,
    get_asset_by_id,
    get_asset_by_fragment
)


def test_asset_counts():
    """Verify that catalog has exactly 10 hairstyles + bald (11) and 12 eyebrows."""
    assert len(HAIRSTYLE_CATALOG) == 11
    assert len(EYEBROW_CATALOG) == 12
    assert len(VERIFIED_ASSET_ALLOWLIST) == 23


def test_bald_asset():
    """Verify bald asset has None fragment and correct object type."""
    bald = HAIRSTYLE_CATALOG["bald"]
    assert bald.asset_id == "bald"
    assert bald.fragment is None
    assert bald.object_type == "Hair"
    assert bald.display_name == "Bald"


def test_hairstyle_fragments():
    """Verify all installed hairstyles have valid .mhclo fragment paths."""
    expected = {
        "afro01": "afro01/afro01.mhclo",
        "bob01": "bob01/bob01.mhclo",
        "bob02": "bob02/bob02.mhclo",
        "braid01": "braid01/braid01.mhclo",
        "long01": "long01/long01.mhclo",
        "ponytail01": "ponytail01/ponytail01.mhclo",
        "short01": "short01/short01.mhclo",
        "short02": "short02/short02.mhclo",
        "short03": "short03/short03.mhclo",
        "short04": "short04/short04.mhclo",
    }
    for asset_id, fragment in expected.items():
        assert asset_id in HAIRSTYLE_CATALOG
        assert HAIRSTYLE_CATALOG[asset_id].fragment == fragment
        assert HAIRSTYLE_CATALOG[asset_id].object_type == "Hair"


def test_eyebrow_fragments():
    """Verify all 12 eyebrow assets have valid .mhclo fragment paths."""
    for i in range(1, 13):
        asset_id = f"eyebrow{i:03d}"
        assert asset_id in EYEBROW_CATALOG
        assert EYEBROW_CATALOG[asset_id].fragment == f"{asset_id}/{asset_id}.mhclo"
        assert EYEBROW_CATALOG[asset_id].object_type == "Eyebrows"


def test_find_hair_by_text():
    """Verify natural language matching for hairstyles."""
    cases = [
        ("A suspect with an afro and a wide jaw.", "afro01"),
        ("Change the hairstyle to a bob cut.", "bob01"),
        ("She has a textured bob haircut.", "bob02"),
        ("The witness saw braids.", "braid01"),
        ("A person with long straight hair.", "long01"),
        ("Hair tied back in a ponytail.", "ponytail01"),
        ("He had short hair.", "short01"),
        ("A person with a neat side-parted haircut.", "short02"),
        ("She has a pixie cut.", "short03"),
        ("The suspect had tousled short hair.", "short04"),
        ("Make the suspect bald with thick eyebrows.", "bald"),
        ("The suspect had a shaved head.", "bald"),
        ("No hair on his head.", "bald"),
    ]
    for text, expected_id in cases:
        match = find_hair_by_text(text)
        assert match is not None, f"Failed to match hairstyle in: '{text}'"
        assert match.asset_id == expected_id, f"Expected {expected_id}, got {match.asset_id} in '{text}'"


def test_find_eyebrow_by_text():
    """Verify natural language matching for eyebrows."""
    cases = [
        ("Thin curved eyebrows and prominent cheekbones.", "eyebrow006"),
        ("Make the suspect bald with thick eyebrows.", "eyebrow010"),
        ("A suspect with bushy eyebrows and a square jaw.", "eyebrow011"),
        ("High arched eyebrows.", "eyebrow009"),
        ("Flat straight eyebrows.", "eyebrow007"),
        ("Natural rounded eyebrows.", "eyebrow001"),
    ]
    for text, expected_id in cases:
        match = find_eyebrow_by_text(text)
        assert match is not None, f"Failed to match eyebrow in: '{text}'"
        assert match.asset_id == expected_id, f"Expected {expected_id}, got {match.asset_id} in '{text}'"


def test_unrelated_text_returns_none():
    """Verify that unrelated facial text does not falsely match hair or eyebrows."""
    assert find_hair_by_text("Make the nose wider.") is None
    assert find_eyebrow_by_text("Make the nose wider.") is None
    assert find_hair_by_text("Prominent cheekbones and chiseled jaw.") is None


def test_get_asset_by_fragment():
    """Verify fragment lookup."""
    asset = get_asset_by_fragment("afro01/afro01.mhclo")
    assert asset is not None
    assert asset.asset_id == "afro01"

    asset_eb = get_asset_by_fragment("eyebrow003/eyebrow003.mhclo")
    assert asset_eb is not None
    assert asset_eb.asset_id == "eyebrow003"

    assert get_asset_by_fragment("nonexistent/foo.mhclo") is None

