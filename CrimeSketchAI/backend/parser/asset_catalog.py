"""
Verified Asset Catalog for CrimeSketchAI.

Defines the verified allowlist of MakeHuman MHCLO assets compatible with the
hm08 basemesh on character "Human". Includes verified hairstyles and eyebrows
along with natural-language aliases and lookup utilities.

SAFETY & COMPATIBILITY:
- All assets are verified against C:\\Dept\\MPFB\\data\\hair and eyebrows.
- All assets have zero delete vertices (do not alter or puncture character skin).
- Supported asset operations: 'add_asset' and 'remove_asset' via MPFB MCP Bridge.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re


@dataclass(frozen=True)
class AssetDefinition:
    asset_id: str
    asset_type: str             # "hair" or "eyebrows"
    display_name: str
    fragment: Optional[str]     # e.g. "bob01/bob01.mhclo" or None for bald
    object_type: str            # "Hair" or "Eyebrows" (matches Blender object_type)
    keywords: Tuple[str, ...]   # Natural-language aliases (ordered longest-first for matching)
    description: str


# -----------------------------------------------------------------------------
# HAIRSTYLE ASSET CATALOG (10 Installed Assets + Bald Option)
# -----------------------------------------------------------------------------

HAIRSTYLE_CATALOG: Dict[str, AssetDefinition] = {
    "afro01": AssetDefinition(
        asset_id="afro01",
        asset_type="hair",
        display_name="Afro",
        fragment="afro01/afro01.mhclo",
        object_type="Hair",
        keywords=(
            "voluminous curly hair",
            "voluminous curls",
            "short curly hair",
            "tight curly hair",
            "curly afro hair",
            "curly afro",
            "tight curls",
            "tight curl",
            "short curls",
            "short curl",
            "curly hairstyle",
            "curly haircut",
            "curly style",
            "curly hair",
            "afro haircut",
            "afro style",
            "afro hair",
            "afro",
            "curls",
            "curly",
        ),
        description="Voluminous afro with tight curls."
    ),
    "bob01": AssetDefinition(
        asset_id="bob01",
        asset_type="hair",
        display_name="Bob Cut",
        fragment="bob01/bob01.mhclo",
        object_type="Hair",
        keywords=(
            "classic bob cut",
            "classic bob",
            "short bob cut",
            "short bob",
            "chin-length bob",
            "bob cut",
            "bob haircut",
            "bob style",
            "bob",
        ),
        description="Classic smooth chin-length bob cut."
    ),
    "bob02": AssetDefinition(
        asset_id="bob02",
        asset_type="hair",
        display_name="Textured Bob",
        fragment="bob02/bob02.mhclo",
        object_type="Hair",
        keywords=(
            "textured bob cut",
            "textured bob",
            "wavy bob cut",
            "wavy bob",
            "shaggy bob",
            "layered bob",
            "loose curly hair",
            "loose curls",
            "loose curl",
            "wavy curly hair",
            "wavy curls",
            "wavy curl",
            "curly bob",
            "wavy haircut",
            "wavy hairstyle",
            "wavy hair",
        ),
        description="Textured, wavy, layered bob cut (loose curls)."
    ),
    "braid01": AssetDefinition(
        asset_id="braid01",
        asset_type="hair",
        display_name="Braids",
        fragment="braid01/braid01.mhclo",
        object_type="Hair",
        keywords=(
            "long braided hair",
            "braided hair",
            "cornrows",
            "plait hair",
            "braids",
            "braid",
            "plaits",
            "plait",
        ),
        description="Long braided hair plaits."
    ),
    "long01": AssetDefinition(
        asset_id="long01",
        asset_type="hair",
        display_name="Long Hair",
        fragment="long01/long01.mhclo",
        object_type="Hair",
        keywords=(
            "long straight hair",
            "straight long hair",
            "shoulder-length hair",
            "shoulder length hair",
            "long curly hair",
            "curly long hair",
            "flowing long hair",
            "long curls",
            "long haircut",
            "long hair",
        ),
        description="Long straight flowing hair / long hairstyle."
    ),
    "ponytail01": AssetDefinition(
        asset_id="ponytail01",
        asset_type="hair",
        display_name="Ponytail",
        fragment="ponytail01/ponytail01.mhclo",
        object_type="Hair",
        keywords=(
            "high ponytail",
            "tied back hair",
            "tied-back hair",
            "tied up hair",
            "hair in a ponytail",
            "ponytail haircut",
            "ponytail",
            "pony tail",
        ),
        description="Hair tied back in a high ponytail."
    ),
    "short01": AssetDefinition(
        asset_id="short01",
        asset_type="hair",
        display_name="Short Crop",
        fragment="short01/short01.mhclo",
        object_type="Hair",
        keywords=(
            "short cropped hair",
            "short crop",
            "crew cut",
            "buzz cut",
            "cropped haircut",
            "cropped hair",
            "short haircut",
            "short hair",
        ),
        description="Neat short crop / crew cut (baseline style)."
    ),
    "short02": AssetDefinition(
        asset_id="short02",
        asset_type="hair",
        display_name="Side-Parted Short",
        fragment="short02/short02.mhclo",
        object_type="Hair",
        keywords=(
            "neat side-parted haircut",
            "neat side-parted hair",
            "neat side-parted",
            "side-parted haircut",
            "side-parted hair",
            "side-parted",
            "side parted haircut",
            "side parted hair",
            "side parted",
            "side part hair",
            "side part haircut",
            "side part",
            "comb over",
        ),
        description="Neat side-parted short haircut."
    ),
    "short03": AssetDefinition(
        asset_id="short03",
        asset_type="hair",
        display_name="Pixie Cut",
        fragment="short03/short03.mhclo",
        object_type="Hair",
        keywords=(
            "short pixie cut",
            "pixie haircut",
            "pixie cut",
            "tapered crop",
            "pixie crop",
            "pixie",
        ),
        description="Tapered short pixie cut."
    ),
    "short04": AssetDefinition(
        asset_id="short04",
        asset_type="hair",
        display_name="Tousled Short",
        fragment="short04/short04.mhclo",
        object_type="Hair",
        keywords=(
            "messy short hair",
            "tousled short hair",
            "tousled haircut",
            "tousled hair",
            "spiky short hair",
            "spiky hair",
            "messy crop",
            "messy hair",
            "tousled",
        ),
        description="Tousled, spiky, or messy short hair."
    ),
    "bald": AssetDefinition(
        asset_id="bald",
        asset_type="hair",
        display_name="Bald",
        fragment=None,
        object_type="Hair",
        keywords=(
            "clean shaven head",
            "shaved head",
            "hairless head",
            "no hair",
            "hairless",
            "bald head",
            "shaved",
            "bald",
        ),
        description="No hair / completely shaved bald scalp."
    )
}


# -----------------------------------------------------------------------------
# EYEBROW ASSET CATALOG (12 Installed Assets)
# -----------------------------------------------------------------------------

EYEBROW_CATALOG: Dict[str, AssetDefinition] = {
    "eyebrow001": AssetDefinition(
        asset_id="eyebrow001",
        asset_type="eyebrows",
        display_name="Natural Rounded Eyebrows",
        fragment="eyebrow001/eyebrow001.mhclo",
        object_type="Eyebrows",
        keywords=(
            "natural rounded eyebrows",
            "soft rounded eyebrows",
            "natural arch eyebrows",
            "natural eyebrows",
            "rounded eyebrows",
        ),
        description="Natural rounded arched eyebrows."
    ),
    "eyebrow002": AssetDefinition(
        asset_id="eyebrow002",
        asset_type="eyebrows",
        display_name="Straight Soft Eyebrows",
        fragment="eyebrow002/eyebrow002.mhclo",
        object_type="Eyebrows",
        keywords=(
            "straight soft eyebrows",
            "flat soft eyebrows",
            "soft straight eyebrows",
            "soft eyebrows",
        ),
        description="Straight soft eyebrows."
    ),
    "eyebrow003": AssetDefinition(
        asset_id="eyebrow003",
        asset_type="eyebrows",
        display_name="Subtle Medium Eyebrows",
        fragment="eyebrow003/eyebrow003.mhclo",
        object_type="Eyebrows",
        keywords=(
            "subtle medium eyebrows",
            "subtle eyebrows",
            "medium eyebrows",
            "average eyebrows",
            "normal eyebrows",
            "standard eyebrows",
        ),
        description="Subtle medium-thickness eyebrows (baseline style)."
    ),
    "eyebrow004": AssetDefinition(
        asset_id="eyebrow004",
        asset_type="eyebrows",
        display_name="Sharp Arched Eyebrows",
        fragment="eyebrow004/eyebrow004.mhclo",
        object_type="Eyebrows",
        keywords=(
            "sharp arched eyebrows",
            "high peaked eyebrows",
            "sharp eyebrows",
            "peaked eyebrows",
        ),
        description="Sharp angled eyebrows with a high peak."
    ),
    "eyebrow005": AssetDefinition(
        asset_id="eyebrow005",
        asset_type="eyebrows",
        display_name="Defined Tapered Eyebrows",
        fragment="eyebrow005/eyebrow005.mhclo",
        object_type="Eyebrows",
        keywords=(
            "defined tapered eyebrows",
            "sculpted eyebrows",
            "tapered eyebrows",
            "defined eyebrows",
        ),
        description="Clearly defined, sculpted, tapered eyebrows."
    ),
    "eyebrow006": AssetDefinition(
        asset_id="eyebrow006",
        asset_type="eyebrows",
        display_name="Thin Curved Eyebrows",
        fragment="eyebrow006/eyebrow006.mhclo",
        object_type="Eyebrows",
        keywords=(
            "pencil thin eyebrows",
            "pencil-thin eyebrows",
            "thin curved eyebrows",
            "fine thin eyebrows",
            "narrow eyebrows",
            "slender eyebrows",
            "thin eyebrows",
            "fine eyebrows",
        ),
        description="Thin, slender, curved pencil eyebrows."
    ),
    "eyebrow007": AssetDefinition(
        asset_id="eyebrow007",
        asset_type="eyebrows",
        display_name="Straight Eyebrows",
        fragment="eyebrow007/eyebrow007.mhclo",
        object_type="Eyebrows",
        keywords=(
            "flat horizontal eyebrows",
            "horizontal eyebrows",
            "straight flat eyebrows",
            "flat eyebrows",
            "straight eyebrows",
        ),
        description="Flat, straight, horizontal eyebrows."
    ),
    "eyebrow008": AssetDefinition(
        asset_id="eyebrow008",
        asset_type="eyebrows",
        display_name="Angled Eyebrows",
        fragment="eyebrow008/eyebrow008.mhclo",
        object_type="Eyebrows",
        keywords=(
            "upward angled eyebrows",
            "slanting eyebrows",
            "angled eyebrows",
        ),
        description="Upward angled, slanting eyebrows."
    ),
    "eyebrow009": AssetDefinition(
        asset_id="eyebrow009",
        asset_type="eyebrows",
        display_name="Arched Eyebrows",
        fragment="eyebrow009/eyebrow009.mhclo",
        object_type="Eyebrows",
        keywords=(
            "high arched eyebrows",
            "high arch eyebrows",
            "curved arched eyebrows",
            "curved eyebrows",
            "arched eyebrows",
            "arch eyebrows",
        ),
        description="Prominent arched, curved eyebrows."
    ),
    "eyebrow010": AssetDefinition(
        asset_id="eyebrow010",
        asset_type="eyebrows",
        display_name="Thick Eyebrows",
        fragment="eyebrow010/eyebrow010.mhclo",
        object_type="Eyebrows",
        keywords=(
            "thick dense eyebrows",
            "heavy thick eyebrows",
            "full thick eyebrows",
            "dense eyebrows",
            "heavy eyebrows",
            "thick eyebrows",
            "full eyebrows",
        ),
        description="Dense, thick, heavy eyebrows."
    ),
    "eyebrow011": AssetDefinition(
        asset_id="eyebrow011",
        asset_type="eyebrows",
        display_name="Bushy Eyebrows",
        fragment="eyebrow011/eyebrow011.mhclo",
        object_type="Eyebrows",
        keywords=(
            "very thick bushy eyebrows",
            "heavy bushy eyebrows",
            "wild bushy eyebrows",
            "coarse eyebrows",
            "bushy eyebrows",
            "bushy brow",
            "bushy",
        ),
        description="Coarse, bushy, overgrown eyebrows."
    ),
    "eyebrow012": AssetDefinition(
        asset_id="eyebrow012",
        asset_type="eyebrows",
        display_name="Wide Full Eyebrows",
        fragment="eyebrow012/eyebrow012.mhclo",
        object_type="Eyebrows",
        keywords=(
            "full coverage eyebrows",
            "wide full eyebrows",
            "broad full eyebrows",
            "wide eyebrows",
            "broad eyebrows",
        ),
        description="Broad, wide full-coverage eyebrows."
    )
}

# Complete combined verified asset allowlist
VERIFIED_ASSET_ALLOWLIST: Dict[str, AssetDefinition] = {
    **HAIRSTYLE_CATALOG,
    **EYEBROW_CATALOG
}


# -----------------------------------------------------------------------------
# LOOKUP & MATCHING UTILITIES
# -----------------------------------------------------------------------------

def find_hair_match(text: str) -> Optional[Tuple[AssetDefinition, str]]:
    """
    Finds a matching hairstyle and the matched keyword from natural language text.
    Returns (AssetDefinition, matched_keyword) or None.
    """
    clean_text = text.lower()
    best_match: Optional[AssetDefinition] = None
    best_kw: str = ""
    longest_kw_len = 0

    for asset in HAIRSTYLE_CATALOG.values():
        for kw in asset.keywords:
            pattern = rf'\b{re.escape(kw)}\b'
            if re.search(pattern, clean_text):
                if len(kw) > longest_kw_len:
                    longest_kw_len = len(kw)
                    best_match = asset
                    best_kw = kw

    return (best_match, best_kw) if best_match else None


def find_hair_by_text(text: str) -> Optional[AssetDefinition]:
    """
    Finds a matching hairstyle from natural language text.
    Returns None if no matching hairstyle is detected.
    """
    match = find_hair_match(text)
    return match[0] if match else None


def find_eyebrow_match(text: str) -> Optional[Tuple[AssetDefinition, str]]:
    """
    Finds a matching eyebrow asset and the matched keyword from natural language text.
    Returns (AssetDefinition, matched_keyword) or None.
    """
    clean_text = text.lower()
    best_match: Optional[AssetDefinition] = None
    best_kw: str = ""
    longest_kw_len = 0

    for asset in EYEBROW_CATALOG.values():
        for kw in asset.keywords:
            pattern = rf'\b{re.escape(kw)}\b'
            if re.search(pattern, clean_text):
                if len(kw) > longest_kw_len:
                    longest_kw_len = len(kw)
                    best_match = asset
                    best_kw = kw

    return (best_match, best_kw) if best_match else None


def find_eyebrow_by_text(text: str) -> Optional[AssetDefinition]:
    """
    Finds a matching eyebrow asset from natural language text.
    Returns None if no matching eyebrow asset is detected.
    """
    match = find_eyebrow_match(text)
    return match[0] if match else None


def get_asset_by_id(asset_id: str) -> Optional[AssetDefinition]:
    """Retrieves an AssetDefinition by exact asset_id."""
    return VERIFIED_ASSET_ALLOWLIST.get(asset_id.strip().lower())


def get_asset_by_fragment(fragment: str) -> Optional[AssetDefinition]:
    """Retrieves an AssetDefinition by its MHCLO fragment path."""
    clean = fragment.strip().lower()
    for asset in VERIFIED_ASSET_ALLOWLIST.values():
        if asset.fragment and asset.fragment.lower() == clean:
            return asset
    return None


# -----------------------------------------------------------------------------
# CANONICAL ALIASES & RESOLUTION UTILITIES
# -----------------------------------------------------------------------------

HAIRSTYLE_ALIASES: Dict[str, str] = {
    # Curly hair aliases -> afro01 (afro with tight curls)
    "curly": "afro01",
    "curls": "afro01",
    "curly_hair": "afro01",
    "curly hair": "afro01",
    "curly_haircut": "afro01",
    "curly haircut": "afro01",
    "curly_hairstyle": "afro01",
    "curly hairstyle": "afro01",
    "short_curly_hair": "afro01",
    "short curly hair": "afro01",
    "short_curls": "afro01",
    "short curls": "afro01",
    "tight_curls": "afro01",
    "tight curls": "afro01",
    "tight_curl": "afro01",
    "tight curl": "afro01",
    "tight_curly_hair": "afro01",
    "tight curly hair": "afro01",
    "voluminous_curls": "afro01",
    "voluminous curls": "afro01",
    "voluminous_curly_hair": "afro01",
    "voluminous curly hair": "afro01",
    "curly_afro": "afro01",
    "curly afro": "afro01",
    "afro": "afro01",
    "afro_hair": "afro01",
    "afro hair": "afro01",

    # Loose curls / wavy aliases -> bob02 (textured wavy bob)
    "loose_curls": "bob02",
    "loose curls": "bob02",
    "loose_curl": "bob02",
    "loose curl": "bob02",
    "loose_curly_hair": "bob02",
    "loose curly hair": "bob02",
    "wavy": "bob02",
    "wavy_hair": "bob02",
    "wavy hair": "bob02",
    "wavy_curls": "bob02",
    "wavy curls": "bob02",
    "wavy_bob": "bob02",
    "wavy bob": "bob02",
    "textured_bob": "bob02",
    "textured bob": "bob02",
    "shaggy_bob": "bob02",
    "shaggy bob": "bob02",
    "curly_bob": "bob02",
    "curly bob": "bob02",

    # Long hair / long curly aliases -> long01
    "long_curly_hair": "long01",
    "long curly hair": "long01",
    "curly_long_hair": "long01",
    "curly long hair": "long01",
    "long_curls": "long01",
    "long curls": "long01",
    "long_hair": "long01",
    "long hair": "long01",
    "straight_long_hair": "long01",
    "straight long hair": "long01",
    "shoulder_length": "long01",
    "shoulder length": "long01",

    # Bob cut aliases -> bob01
    "bob": "bob01",
    "bob_cut": "bob01",
    "bob cut": "bob01",
    "chin_length_bob": "bob01",
    "chin length bob": "bob01",

    # Braids aliases -> braid01
    "braids": "braid01",
    "braid": "braid01",
    "cornrows": "braid01",
    "plaits": "braid01",

    # Ponytail aliases -> ponytail01
    "ponytail": "ponytail01",
    "pony_tail": "ponytail01",
    "pony tail": "ponytail01",
    "tied_back_hair": "ponytail01",
    "tied back hair": "ponytail01",

    # Short crop aliases -> short01
    "short_hair": "short01",
    "short hair": "short01",
    "short_crop": "short01",
    "short crop": "short01",
    "crew_cut": "short01",
    "crew cut": "short01",
    "buzz_cut": "short01",
    "buzz cut": "short01",

    # Side-parted aliases -> short02
    "side_part": "short02",
    "side part": "short02",
    "side_parted": "short02",
    "side parted": "short02",
    "comb_over": "short02",
    "comb over": "short02",

    # Pixie cut aliases -> short03
    "pixie": "short03",
    "pixie_cut": "short03",
    "pixie cut": "short03",

    # Tousled aliases -> short04
    "tousled": "short04",
    "messy_hair": "short04",
    "messy hair": "short04",
    "spiky_hair": "short04",
    "spiky hair": "short04",

    # Bald aliases -> bald
    "bald": "bald",
    "shaved": "bald",
    "shaved_head": "bald",
    "shaved head": "bald",
    "hairless": "bald",
    "no_hair": "bald",
    "no hair": "bald",
}

EYEBROW_ALIASES: Dict[str, str] = {
    "natural_rounded": "eyebrow001",
    "natural rounded": "eyebrow001",
    "straight_soft": "eyebrow002",
    "straight soft": "eyebrow002",
    "subtle_medium": "eyebrow003",
    "subtle medium": "eyebrow003",
    "sharp_arched": "eyebrow004",
    "sharp arched": "eyebrow004",
    "defined_tapered": "eyebrow005",
    "defined tapered": "eyebrow005",
    "thin_curved": "eyebrow006",
    "thin curved": "eyebrow006",
    "pencil_thin": "eyebrow006",
    "pencil thin": "eyebrow006",
    "thin": "eyebrow006",
    "thin_eyebrows": "eyebrow006",
    "thin eyebrows": "eyebrow006",
    "straight": "eyebrow007",
    "straight_eyebrows": "eyebrow007",
    "straight eyebrows": "eyebrow007",
    "angled": "eyebrow008",
    "angled_eyebrows": "eyebrow008",
    "angled eyebrows": "eyebrow008",
    "arched": "eyebrow009",
    "arched_eyebrows": "eyebrow009",
    "arched eyebrows": "eyebrow009",
    "thick": "eyebrow010",
    "thick_eyebrows": "eyebrow010",
    "thick eyebrows": "eyebrow010",
    "bushy": "eyebrow011",
    "bushy_eyebrows": "eyebrow011",
    "bushy eyebrows": "eyebrow011",
    "wide_full": "eyebrow012",
    "wide full": "eyebrow012",
}


def resolve_hairstyle(identifier_or_text: str) -> Optional[AssetDefinition]:
    """
    Resolves an asset ID, alias, or natural language phrase to a verified AssetDefinition.
    Returns None if the hairstyle cannot be mapped to a verified catalog asset.
    Strictly preserves the allowlist - never returns an unverified asset.
    """
    if not identifier_or_text or not identifier_or_text.strip():
        return None

    clean = identifier_or_text.strip().lower()

    # 1. Exact catalog ID match
    if clean in HAIRSTYLE_CATALOG:
        return HAIRSTYLE_CATALOG[clean]

    # 2. Explicit alias dictionary match
    if clean in HAIRSTYLE_ALIASES:
        canonical_id = HAIRSTYLE_ALIASES[clean]
        return HAIRSTYLE_CATALOG.get(canonical_id)

    clean_spaced = clean.replace('_', ' ')
    if clean_spaced in HAIRSTYLE_ALIASES:
        canonical_id = HAIRSTYLE_ALIASES[clean_spaced]
        return HAIRSTYLE_CATALOG.get(canonical_id)

    # 3. Natural language keyword search
    matched = find_hair_by_text(clean_spaced)
    if matched:
        return matched

    return None


def resolve_eyebrow(identifier_or_text: str) -> Optional[AssetDefinition]:
    """
    Resolves an eyebrow ID, alias, or natural language phrase to a verified AssetDefinition.
    Returns None if the eyebrow style cannot be mapped to a verified catalog asset.
    """
    if not identifier_or_text or not identifier_or_text.strip():
        return None

    clean = identifier_or_text.strip().lower()

    if clean in EYEBROW_CATALOG:
        return EYEBROW_CATALOG[clean]

    if clean in EYEBROW_ALIASES:
        canonical_id = EYEBROW_ALIASES[clean]
        return EYEBROW_CATALOG.get(canonical_id)

    clean_spaced = clean.replace('_', ' ')
    if clean_spaced in EYEBROW_ALIASES:
        canonical_id = EYEBROW_ALIASES[clean_spaced]
        return EYEBROW_CATALOG.get(canonical_id)

    matched = find_eyebrow_by_text(clean_spaced)
    if matched:
        return matched

    return None


def get_supported_hairstyles_summary() -> str:
    """Returns a formatted human-readable list of supported hairstyles."""
    items = [
        "Afro / Curly (tight curls: afro01)",
        "Classic Bob (bob01)",
        "Textured Bob / Wavy (loose curls: bob02)",
        "Braids (braid01)",
        "Long Hair (long01)",
        "Ponytail (ponytail01)",
        "Short Crop / Crew Cut (short01)",
        "Side-Parted Short (short02)",
        "Pixie Cut (short03)",
        "Tousled Short (short04)",
        "Bald (bald)"
    ]
    return ", ".join(items)


def get_unsupported_hairstyle_error(requested: Optional[str] = None) -> str:
    """Returns a clear explanatory error message for unsupported hairstyle requests."""
    prefix = f"Hairstyle '{requested}' is not supported. " if requested else "Hair modifications are not supported without selecting a verified hairstyle from the catalog. "
    return f"{prefix}Supported hairstyles: {get_supported_hairstyles_summary()}."
