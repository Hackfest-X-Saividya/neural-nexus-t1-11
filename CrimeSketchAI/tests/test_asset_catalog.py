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
    get_asset_by_fragment,
    resolve_hairstyle,
    resolve_eyebrow,
    get_supported_hairstyles_summary,
    get_unsupported_hairstyle_error
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


def test_curly_hair_natural_language_variations():
    """Verify natural language matching for curly hairstyle variations."""
    cases = [
        ("The suspect has curly hair.", "afro01"),
        ("A person with short curly hair.", "afro01"),
        ("The witness described long curly hair.", "long01"),
        ("He had tight curls on his head.", "afro01"),
        ("She had loose curls.", "bob02"),
        ("A suspect with loose curly hair.", "bob02"),
        ("He had wavy curls.", "bob02"),
        ("Voluminous curly hair.", "afro01"),
        ("A person with curly afro.", "afro01"),
        ("Make the hair curly.", "afro01"),
        ("The suspect has curls.", "afro01"),
    ]
    for text, expected_id in cases:
        match = find_hair_by_text(text)
        assert match is not None, f"Failed to match hairstyle in: '{text}'"
        assert match.asset_id == expected_id, f"Expected {expected_id}, got {match.asset_id} in '{text}'"


def test_resolve_hairstyle_canonical_and_aliases():
    """Verify resolve_hairstyle maps IDs, snake_case variants, and aliases to canonical assets."""
    # Exact IDs
    assert resolve_hairstyle("afro01").asset_id == "afro01"
    assert resolve_hairstyle("bob01").asset_id == "bob01"
    assert resolve_hairstyle("bob02").asset_id == "bob02"
    assert resolve_hairstyle("long01").asset_id == "long01"
    assert resolve_hairstyle("bald").asset_id == "bald"

    # Curly aliases
    assert resolve_hairstyle("curly").asset_id == "afro01"
    assert resolve_hairstyle("curly_hair").asset_id == "afro01"
    assert resolve_hairstyle("curly hair").asset_id == "afro01"
    assert resolve_hairstyle("curls").asset_id == "afro01"
    assert resolve_hairstyle("tight_curls").asset_id == "afro01"
    assert resolve_hairstyle("tight curls").asset_id == "afro01"
    assert resolve_hairstyle("short_curly_hair").asset_id == "afro01"
    assert resolve_hairstyle("short curly hair").asset_id == "afro01"

    # Loose curls / wavy aliases
    assert resolve_hairstyle("loose_curls").asset_id == "bob02"
    assert resolve_hairstyle("loose curls").asset_id == "bob02"
    assert resolve_hairstyle("wavy").asset_id == "bob02"
    assert resolve_hairstyle("wavy_hair").asset_id == "bob02"
    assert resolve_hairstyle("curly_bob").asset_id == "bob02"

    # Long curly aliases
    assert resolve_hairstyle("long_curly_hair").asset_id == "long01"
    assert resolve_hairstyle("long curly hair").asset_id == "long01"


def test_resolve_hairstyle_strict_allowlist_enforcement():
    """Verify that unverified/arbitrary hairstyles return None and cannot bypass allowlist."""
    unsupported = [
        "dreadlocks",
        "dreads",
        "mohawk",
        "mullet",
        "rainbow_hair",
        "perm",
        "fade",
        "undercut",
        "unknown_hair_123",
        "DROP TABLE users;",
        "",
        "   "
    ]
    for raw in unsupported:
        assert resolve_hairstyle(raw) is None, f"Expected None for unsupported hairstyle '{raw}'"


def test_get_supported_hairstyles_summary():
    """Verify supported hairstyles summary lists all verified catalog styles."""
    summary = get_supported_hairstyles_summary()
    assert "afro01" in summary
    assert "bob01" in summary
    assert "bob02" in summary
    assert "braid01" in summary
    assert "long01" in summary
    assert "ponytail01" in summary
    assert "short01" in summary
    assert "short02" in summary
    assert "short03" in summary
    assert "short04" in summary
    assert "bald" in summary
    assert "loose curls" in summary
    assert "tight curls" in summary


def test_get_unsupported_hairstyle_error():
    """Verify clear error message for unsupported hairstyles."""
    err = get_unsupported_hairstyle_error("dreadlocks")
    assert "Hairstyle 'dreadlocks' is not supported." in err
    assert "Supported hairstyles:" in err
    assert "afro01" in err
    assert "bob02" in err

