"""
Refinement Parser for CrimeSketchAI.

Parses natural language requests into structured, validated feature adjustments
strictly adhering to the verified 10-feature allowlist.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple, List
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST, FeatureDefinition
from backend.parser.asset_catalog import (
    HAIRSTYLE_CATALOG,
    EYEBROW_CATALOG,
    VERIFIED_ASSET_ALLOWLIST,
    AssetDefinition,
    find_hair_by_text,
    find_eyebrow_by_text,
    find_hair_match,
    find_eyebrow_match,
    resolve_hairstyle,
    get_supported_hairstyles_summary,
    get_unsupported_hairstyle_error
)

@dataclass
class ParsedAssetAdjustment:
    asset_type: str        # "hair" or "eyebrows"
    asset_id: str          # e.g. "afro01", "bald", "eyebrow006"
    display_name: str
    fragment: Optional[str]
    object_type: str       # "Hair" or "Eyebrows"
    action: str            # "swap", "remove", "add"

@dataclass
class ParsedRefinement:
    raw_text: str
    feature_id: str
    display_name: str
    section: str
    category: str
    is_sided: bool
    side: str
    direction: int            # +1 for increase, -1 for decrease
    magnitude: float          # e.g. 0.05
    delta: float              # direction * magnitude
    target_identifier: str    # e.g. "nose:nose-scale-horiz-decr-incr:unsided"
    target_shapekey: str      # positive or negative target depending on direction
    features: Optional[List['ParsedRefinement']] = None
    asset_adjustments: Optional[List[ParsedAssetAdjustment]] = None

    def __iter__(self):
        items = self.features if self.features is not None else [self]
        return iter(items)

    def __len__(self):
        items = self.features if self.features is not None else [self]
        return len(items)

    def __getitem__(self, idx):
        items = self.features if self.features is not None else [self]
        return items[idx]


class ParseError(Exception):
    """Raised when an instruction cannot be safely parsed or mapped."""
    pass


UNSUPPORTED_DOMAINS = [
    (r'\b(blonde|blond|brunette|redhead|dye|dyed|bleach|bleached)\b', "Hair color and dye modifications are not supported in this allowlist."),
    (r'\b(hair\s*colou?r|black\s*hair|brown\s*hair|red\s*hair|grey\s*hair|gray\s*hair|white\s*hair)\b', "Hair color modifications are not supported in this allowlist."),
    (r'\b(beard|mustache|goatee|facial hair|stubble|sideburns)\b', "Beard and facial hair are not supported in structural geometry."),
    (r'\bskin\b', "Skin material/tone modifications are handled via skin tools, not structural geometry."),
    (r'\b(complexion|fair skin|dark skin|pale skin)\b', "Skin complexion is handled via skin tools, not structural geometry."),
    (r'\b(expression|expressions)\b', "Facial expressions are handled through expression/face-unit tools, not structural geometry."),
    (r'\bsmil(e|ing|ey)?\b', "Smiling is an expression unit. This tool refines structural suspect geometry."),
    (r'\bfrown(ing)?\b', "Frowning is an expression unit. This tool refines structural suspect geometry."),
    (r'\bhapp(y|ier)\b', "Emotional expressions are handled through ARKit face units, not structural geometry."),
    (r'\bangr(y|ier)\b', "Emotional expressions are handled through ARKit face units, not structural geometry."),
    (r'\bsad(der)?\b', "Emotional expressions are handled through ARKit face units, not structural geometry."),
    (r'\bage\b', "Overall age is a macro phenotype parameter, not a local target modifier."),
    (r'\bgender\b', "Gender is a macro phenotype parameter, not a local target modifier."),
    (r'\b(race|ethnicity)\b', "Ethnicity/race is a macro phenotype parameter, not a local target modifier."),
]


class RefinementParser:
    def __init__(self, default_step: float = 0.05):
        self.default_step = default_step

    def parse(self, text: str) -> ParsedRefinement:
        if not text or not text.strip():
            raise ParseError("Request text cannot be empty.")

        cleaned = text.strip()
        lower = cleaned.lower()

        # Check for unsupported domains
        for pattern, msg in UNSUPPORTED_DOMAINS:
            if re.search(pattern, lower):
                raise ParseError(f"Unsupported request: {msg}")

        # Check for hairstyle assets
        hair_match = find_hair_match(lower)
        hair_asset = None
        if hair_match:
            hair_asset, h_kw = hair_match
            # Check if a second distinct hairstyle is present in the remaining text
            remainder = re.sub(rf'\b{re.escape(h_kw)}\b', '', lower, count=1)
            second_h = find_hair_match(remainder)
            if second_h and second_h[0].asset_id != hair_asset.asset_id:
                raise ParseError("Conflicting hairstyle instructions detected. Please specify only one hairstyle.")

        # If user explicitly asks for hair modification or mentions hairstyles/curls/cuts but it doesn't match any catalog style
        unsupported_hair_pattern = r'\b(hair|hairstyles?|haircut|curls?|dreadlocks?|dreads|mohawk|mullet|fade|undercut|perm|wig|extensions?)\b'
        if not hair_asset:
            hair_term_match = re.search(unsupported_hair_pattern, lower)
            if hair_term_match:
                term = hair_term_match.group(1)
                raise ParseError(
                    f"Hair modifications are not supported without selecting a verified hairstyle from the catalog. "
                    f"Requested style '{term}' is not in the allowlist. "
                    f"Supported hairstyles: {get_supported_hairstyles_summary()}."
                )

        # Check for eyebrow assets
        eyebrow_match = find_eyebrow_match(lower)
        eyebrow_asset = None
        if eyebrow_match:
            eyebrow_asset, eb_kw = eyebrow_match
            # Check if a second distinct eyebrow style is present in the remaining text
            remainder = re.sub(rf'\b{re.escape(eb_kw)}\b', '', lower, count=1)
            second_eb = find_eyebrow_match(remainder)
            if second_eb and second_eb[0].asset_id != eyebrow_asset.asset_id:
                raise ParseError("Conflicting eyebrow instructions detected. Please specify only one eyebrow style.")

        parsed_assets: List[ParsedAssetAdjustment] = []
        if hair_asset:
            action = "remove" if hair_asset.asset_id == "bald" else "swap"
            parsed_assets.append(ParsedAssetAdjustment(
                asset_type="hair",
                asset_id=hair_asset.asset_id,
                display_name=hair_asset.display_name,
                fragment=hair_asset.fragment,
                object_type=hair_asset.object_type,
                action=action
            ))
        if eyebrow_asset:
            parsed_assets.append(ParsedAssetAdjustment(
                asset_type="eyebrows",
                asset_id=eyebrow_asset.asset_id,
                display_name=eyebrow_asset.display_name,
                fragment=eyebrow_asset.fragment,
                object_type=eyebrow_asset.object_type,
                action="swap"
            ))

        # If assets are present, strip their matched keywords from the geometry text
        # so asset adjectives like "thin", "thick", "short", "wide" don't conflict with facial geometry directions
        geom_text = lower
        if hair_match:
            geom_text = re.sub(rf'\b{re.escape(hair_match[1])}\b', ' ', geom_text)
        if eyebrow_match:
            geom_text = re.sub(rf'\b{re.escape(eyebrow_match[1])}\b', ' ', geom_text)

        # Check for multiple compound geometry commands (e.g. "nose wider and eyes larger")
        # When assets are present, "and" can connect the asset with the geometry feature (e.g. "afro and wide jaw")
        if not parsed_assets:
            if re.search(r'\b(and|as well as|also)\b', lower) or ';' in lower:
                raise ParseError("Multiple compound instructions detected. Please provide one feature adjustment per request.")

        # If assets are present, check if any geometry adjustment is also specified
        if parsed_assets:
            try:
                feature_def, direction = self._detect_feature_and_direction(geom_text)
                magnitude = self._detect_magnitude(geom_text)
                delta = round(direction * magnitude, 4)
                target_shapekey = feature_def.positive_target if direction > 0 else feature_def.negative_target
                target_id = f"{feature_def.section}:{feature_def.category}:{feature_def.side}"

                single_geom = ParsedRefinement(
                    raw_text=cleaned,
                    feature_id=feature_def.feature_id,
                    display_name=feature_def.display_name,
                    section=feature_def.section,
                    category=feature_def.category,
                    is_sided=feature_def.is_sided,
                    side=feature_def.side,
                    direction=direction,
                    magnitude=magnitude,
                    delta=delta,
                    target_identifier=target_id,
                    target_shapekey=target_shapekey,
                    features=None,
                    asset_adjustments=parsed_assets
                )
                single_geom.features = [single_geom]
                return single_geom
            except ParseError as pe:
                err_str = str(pe)
                if "Could not identify an allowlisted facial feature" in err_str:
                    # Pure asset adjustment with no geometry modifications
                    return ParsedRefinement(
                        raw_text=cleaned,
                        feature_id="asset_customization",
                        display_name="Hair / Eyebrow Customization",
                        section="asset",
                        category="asset",
                        is_sided=False,
                        side="unsided",
                        direction=0,
                        magnitude=0.0,
                        delta=0.0,
                        target_identifier="asset:customization",
                        target_shapekey="",
                        features=[],
                        asset_adjustments=parsed_assets
                    )
                else:
                    # Ambiguous or conflicting geometry instruction (e.g. "nose wider narrower with afro")
                    raise pe

        # Pure geometry adjustment (no assets)
        magnitude = self._detect_magnitude(lower)
        feature_def, direction = self._detect_feature_and_direction(lower)
        delta = round(direction * magnitude, 4)
        target_shapekey = feature_def.positive_target if direction > 0 else feature_def.negative_target
        target_id = f"{feature_def.section}:{feature_def.category}:{feature_def.side}"

        return ParsedRefinement(
            raw_text=cleaned,
            feature_id=feature_def.feature_id,
            display_name=feature_def.display_name,
            section=feature_def.section,
            category=feature_def.category,
            is_sided=feature_def.is_sided,
            side=feature_def.side,
            direction=direction,
            magnitude=magnitude,
            delta=delta,
            target_identifier=target_id,
            target_shapekey=target_shapekey,
            features=None,
            asset_adjustments=None
        )

    def _detect_magnitude(self, text: str) -> float:
        if re.search(r'\b(slightly|a bit|a little|subtly|mildly|minor)\b', text):
            return 0.05
        if re.search(r'\b(significantly|much|a lot|considerably|greatly)\b', text):
            return 0.10
        if re.search(r'\b(moderately|medium)\b', text):
            return 0.08
        return self.default_step

    def _detect_feature_and_direction(self, text: str) -> Tuple[FeatureDefinition, int]:
        # 1. Brow Ridge / Eyebrows
        if re.search(r'\b(brow\s*ridge|brow\s*bone|heavy\s*brow|supraorbital)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["brow_ridge"])
            return VERIFIED_ALLOWLIST["brow_ridge"], direction

        # 2. Temples / Forehead
        if re.search(r'\b(temple|temples)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["temple_width"])
            return VERIFIED_ALLOWLIST["temple_width"], direction

        if re.search(r'\bforehead\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["forehead_size"])
            return VERIFIED_ALLOWLIST["forehead_size"], direction

        # 3. Ears
        if re.search(r'\b(earlobe|earlobes|ear\s*lobe|ear\s*lobes)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["ear_lobe_size"])
            return VERIFIED_ALLOWLIST["ear_lobe_size"], direction

        if re.search(r'\b(ears?)\b', text):
            if re.search(r'\b(stick\w*\s*out|protrud\w*|prominen\w*|flared?|wing\w*|pinned)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["ear_protrusion"])
                return VERIFIED_ALLOWLIST["ear_protrusion"], direction
            elif re.search(r'\b(length|long\w*|tall\w*|short\w*|elongat\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["ear_vertical_length"])
                return VERIFIED_ALLOWLIST["ear_vertical_length"], direction
            else:
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["ear_size"])
                return VERIFIED_ALLOWLIST["ear_size"], direction

        # 4. Eyes & Eyelids
        if re.search(r'\b(bags|under[- ]eye|eye\s*bags|puffy\s*eyes?)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["under_eye_bags"])
            return VERIFIED_ALLOWLIST["under_eye_bags"], direction

        if re.search(r'\b(hooded|eyelids?|eyefolds?|epicanthic)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["hooded_eyelids"])
            return VERIFIED_ALLOWLIST["hooded_eyelids"], direction

        if re.search(r'\b(wide[- ]set|close[- ]set|far\s*apart|closer\s*together|narrow[- ]set)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["eye_spacing"])
            return VERIFIED_ALLOWLIST["eye_spacing"], direction

        if re.search(r'\b(canthal\s*tilt|cat\s*eyes?|slanted\s*eyes?)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["eye_tilt"])
            return VERIFIED_ALLOWLIST["eye_tilt"], direction

        if re.search(r'\b(eyes?|eye size)\b', text):
            if re.search(r'\b(spacing|space|apart|together)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["eye_spacing"])
                return VERIFIED_ALLOWLIST["eye_spacing"], direction
            elif re.search(r'\b(tilt|angle|upturned|downturned|slanted)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["eye_tilt"])
                return VERIFIED_ALLOWLIST["eye_tilt"], direction
            else:
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["eye_size"])
                return VERIFIED_ALLOWLIST["eye_size"], direction

        # 5. Nose & Nostrils
        if re.search(r'\b(nostril|nostrils)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nostril_width"])
            return VERIFIED_ALLOWLIST["nostril_width"], direction

        if re.search(r'\b(dorsal\s*hump|nasal\s*hump|hooked\s*nose|aquiline|roman\s*nose)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nasal_bridge_hump"])
            return VERIFIED_ALLOWLIST["nasal_bridge_hump"], direction

        if re.search(r'\b(bulbous\s*nose|bulbous\s*tip|snub\s*nose|pug\s*nose)\b', text):
            if re.search(r'\b(snub|pug|upturned|droop)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nose_tip_angle"])
                return VERIFIED_ALLOWLIST["nose_tip_angle"], direction
            else:
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nose_tip_width"])
                return VERIFIED_ALLOWLIST["nose_tip_width"], direction

        if re.search(r'\bnose\b', text):
            if re.search(r'\b(hump)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nasal_bridge_hump"])
                return VERIFIED_ALLOWLIST["nasal_bridge_hump"], direction
            elif re.search(r'\b(curve|convex|concave|scooped)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nasal_bridge_curve"])
                return VERIFIED_ALLOWLIST["nasal_bridge_curve"], direction
            elif re.search(r'\b(nostril\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nostril_width"])
                return VERIFIED_ALLOWLIST["nostril_width"], direction
            elif re.search(r'\b(tip\s*angle|tip\s*down|tip\s*up|upturned\s*tip|downturned\s*tip|droop\w*|snub|pug|upturned|downturned)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nose_tip_angle"])
                return VERIFIED_ALLOWLIST["nose_tip_angle"], direction
            elif re.search(r'\b(tip|bulbous|point\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nose_tip_width"])
                return VERIFIED_ALLOWLIST["nose_tip_width"], direction
            elif re.search(r'\b(projection|protrud\w*|depth)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nose_projection"])
                return VERIFIED_ALLOWLIST["nose_projection"], direction
            elif re.search(r'\b(height|tall\w*|short\w*|long\w*|elongat\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nose_height"])
                return VERIFIED_ALLOWLIST["nose_height"], direction
            elif re.search(r'\b(width|wide|wider|narrow\w*|slim\w*|thin\w*|broad\w*|widen)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["nose_width"])
                return VERIFIED_ALLOWLIST["nose_width"], direction
            else:
                raise ParseError("Ambiguous nose instruction. Please specify nose width, height, bridge hump, tip, or nostril width.")

        # 6. Jaw & Chin
        if re.search(r'\b(jaw|jawline|mandible)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["jaw_width"])
            return VERIFIED_ALLOWLIST["jaw_width"], direction

        if re.search(r'\b(cleft\s*chin|chin\s*cleft|dimpled\s*chin|split\s*chin)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["chin_cleft"])
            return VERIFIED_ALLOWLIST["chin_cleft"], direction

        if re.search(r'\bchin\b', text):
            if re.search(r'\b(cleft)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["chin_cleft"])
                return VERIFIED_ALLOWLIST["chin_cleft"], direction
            elif re.search(r'\b(height|tall\w*|short\w*|long\w*|elongat\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["chin_height"])
                return VERIFIED_ALLOWLIST["chin_height"], direction
            elif re.search(r'\b(prominen\w*|forward|protrud\w*|jut\w*|reced\w*|backward)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["chin_prominence"])
                return VERIFIED_ALLOWLIST["chin_prominence"], direction
            elif re.search(r'\b(width|wide|wider|narrow\w*|point\w*|slim\w*|broad\w*|widen)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["chin_width"])
                return VERIFIED_ALLOWLIST["chin_width"], direction
            else:
                raise ParseError("Ambiguous chin instruction. Please specify chin width, prominence, height, or cleft.")

        # 7. Cheeks & Cheekbones
        if re.search(r'\b(dimple|dimples)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["dimples"])
            return VERIFIED_ALLOWLIST["dimples"], direction

        if re.search(r'\b(cheekbone|cheekbones|cheek\s*bones?)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["cheekbone_prominence"])
            return VERIFIED_ALLOWLIST["cheekbone_prominence"], direction

        if re.search(r'\bcheeks?\b', text):
            if re.search(r'\b(volume|chubby|full\w*|puffy|buccal|hollow|sunken|gaunt)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["cheek_volume"])
                return VERIFIED_ALLOWLIST["cheek_volume"], direction
            else:
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["cheekbone_prominence"])
                return VERIFIED_ALLOWLIST["cheekbone_prominence"], direction

        # 8. Mouth, Lips, & Philtrum
        if re.search(r'\b(laugh\s*lines?|nasolabial)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["laugh_lines"])
            return VERIFIED_ALLOWLIST["laugh_lines"], direction

        if re.search(r'\bphiltrum\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["philtrum_depth"])
            return VERIFIED_ALLOWLIST["philtrum_depth"], direction

        if re.search(r'\bcupid(\'s)?\s*bow\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_cupids_bow"])
            return VERIFIED_ALLOWLIST["mouth_cupids_bow"], direction

        if re.search(r'\bupper\s*lip\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_upperlip_volume"])
            return VERIFIED_ALLOWLIST["mouth_upperlip_volume"], direction

        if re.search(r'\blower\s*lip\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_lowerlip_volume"])
            return VERIFIED_ALLOWLIST["mouth_lowerlip_volume"], direction

        if re.search(r'\b(mouth\s*corner|mouth\s*corners|lip\s*corner|lip\s*corners|corner turn|corners?\s+(up|down))\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_corner_turn"])
            return VERIFIED_ALLOWLIST["mouth_corner_turn"], direction

        if re.search(r'\b(plump\s*lips?|full\s*lips?|thin\s*lips?|fuller\s*lips?|thinner\s*lips?|lip\s*height|mouth\s*height)\b', text):
            direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_height"])
            return VERIFIED_ALLOWLIST["mouth_height"], direction

        if re.search(r'\b(mouth|lips?)\b', text):
            if re.search(r'\b(width|wide|wider|narrow\w*|broad\w*|widen)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_width"])
                return VERIFIED_ALLOWLIST["mouth_width"], direction
            elif re.search(r'\b(height|tall\w*|short\w*|full\w*|plump|thin\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_height"])
                return VERIFIED_ALLOWLIST["mouth_height"], direction
            else:
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["mouth_width"])
                return VERIFIED_ALLOWLIST["mouth_width"], direction

        # 9. Head & Cranium
        if re.search(r'\b(head|cranium|skull)\b', text):
            if re.search(r'\b(height|tall\w*|short\w*|long\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["head_height"])
                return VERIFIED_ALLOWLIST["head_height"], direction
            elif re.search(r'\b(width|wide|wider|narrow\w*|slim\w*|broad\w*)\b', text):
                direction = self._resolve_direction(text, VERIFIED_ALLOWLIST["head_width"])
                return VERIFIED_ALLOWLIST["head_width"], direction
            else:
                raise ParseError("Ambiguous head instruction. Please specify head width (e.g. 'wider'/'narrower') or head height (e.g. 'taller'/'shorter').")

        raise ParseError(
            "Could not identify an allowlisted facial feature. "
            f"Supported features ({len(VERIFIED_ALLOWLIST)} verified controls): "
            + ", ".join(f.display_name for f in VERIFIED_ALLOWLIST.values())
        )

    def _resolve_direction(self, text: str, feature_def: FeatureDefinition) -> int:
        # Check explicit compound phrases for prominence/definition first
        is_negated_prominence = bool(re.search(r'\b(less|decrease|reduce)\s+(prominen\w*|pronounced|sculpted|defined|accentuated)\b', text))
        is_pos_prominence = bool(re.search(r'\b(more|increase)\s+(prominen\w*|pronounced|sculpted|defined|accentuated)\b', text))

        if is_negated_prominence and is_pos_prominence:
            raise ParseError(f"Conflicting directions detected for {feature_def.display_name}.")
        if is_negated_prominence:
            return -1
        if is_pos_prominence:
            return 1

        has_decrease = any(re.search(rf'\b{re.escape(kw)}\b', text) for kw in feature_def.decrease_keywords)
        has_increase = any(re.search(rf'\b{re.escape(kw)}\b', text) for kw in feature_def.increase_keywords)

        if re.search(r'\b(increase|enlarge|more|grow|expand|accentuate|wide|wider|widen|broad|broader|larger|bigger|taller|longer|full|fuller|thick|thicker|plump|plumper|chubby|puffy|high|higher|deep|deeper|upturned|convex|protrud\w*|prominen\w*|flare\w*|cleft|hooked|bulbous|aquiline|stick\w*\s*out|wide[- ]set|far\s*apart|hooded|heavy|snub|pug)\b', text):
            has_increase = True
        if re.search(r'\b(decrease|reduce|less|shrink|diminish|narrow\w*|slim\w*|thin\w*|shorter|smaller|flat|flatter|shallow\w*|smooth|faint|downturned|pinned|concave|reced\w*|close[- ]set|closer\s*together|unhooded)\b', text):
            has_decrease = True

        if has_increase and has_decrease:
            raise ParseError(f"Conflicting directions detected for {feature_def.display_name}.")
        if has_increase:
            return 1
        if has_decrease:
            return -1

        raise ParseError(f"Ambiguous or missing adjustment direction for {feature_def.display_name}. Please specify whether to increase/widen or decrease/narrow.")
