"""
Ollama AI Refinement Parser for CrimeSketchAI.

Translates natural-language witness descriptions into validated, structured target adjustments
using a local Ollama LLM (default: qwen3:4b).

Supports both single-feature adjustments and multi-feature composite witness descriptions
applied as a single controlled batch.

SAFETY ARCHITECTURE:
- Prompts model for strict JSON output: {"features": [{"feature_id", "direction", "magnitude"}]}
- Strict allowlist enforcement: every feature_id must exist in VERIFIED_ALLOWLIST.
- Model output is NEVER blindly trusted: exhaustive validation of keys, types,
  ranges, duplicate/conflicting instructions, and domain boundaries.
- Rejects unsupported traits (hair, beard, skin color, age, gender, race, emotions, expressions)
  without silent omission.
- Rejects entire batch if ANY requested adjustment is invalid, ambiguous, or conflicting.
"""

import json
import re
from typing import Optional, Dict, Any, List

from backend.parser.feature_catalog import VERIFIED_ALLOWLIST, FeatureDefinition
from backend.parser.refinement_parser import (
    ParsedRefinement,
    ParsedAssetAdjustment,
    ParseError,
    UNSUPPORTED_DOMAINS
)
from backend.parser.asset_catalog import (
    HAIRSTYLE_CATALOG,
    EYEBROW_CATALOG,
    VERIFIED_ASSET_ALLOWLIST,
    AssetDefinition,
    get_asset_by_id
)
from backend.parser.ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelNotFoundError,
    OllamaResponseError
)

SYSTEM_PROMPT = """You are a specialized forensic assistant for CrimeSketchAI.
Your task is to interpret a witness's natural-language facial description into a structured JSON list of supported 3D facial adjustments.

Map the witness description into a JSON object with a "features" array:
{"features": [{"feature_id": "<id>", "direction": "<increase|decrease>", "magnitude": "<slight|moderate|significant>"}]}

1. "feature_id": MUST be from the 38 verified allowlisted facial geometry controls:
   Core Cranial & Proportions:
   - "head_width": broad, wide head/face -> increase; narrow, slim head/face -> decrease
   - "head_height": tall, long head -> increase; short head -> decrease
   - "forehead_size": tall, high, large forehead -> increase; short, small forehead -> decrease
   - "temple_width": wide temples -> increase; narrow temples -> decrease

   Nose:
   - "nose_width": broad, wide nose -> increase; narrow, slim, thin nose -> decrease
   - "nose_height": longer, taller nose -> increase; shorter nose -> decrease
   - "nasal_bridge_hump": dorsal hump, hooked nose, aquiline nose, roman nose -> increase; straight, smooth bridge -> decrease
   - "nasal_bridge_curve": convex curved bridge -> increase; concave, scooped bridge -> decrease
   - "nostril_width": flared, wide nostrils -> increase; narrow, pinched nostrils -> decrease
   - "nose_tip_width": bulbous tip, broad nose tip, round tip -> increase; pointed, sharp, narrow tip -> decrease
   - "nose_tip_angle": upturned nose, snub nose, tip up -> increase; drooping nose, downturned nose, hooked tip -> decrease
   - "nose_projection": protruding, deep nose -> increase; flat, shallow, receding nose -> decrease

   Mouth & Lips:
   - "mouth_width": wide, broad mouth -> increase; narrow, small mouth -> decrease
   - "mouth_height": full lips, plump lips, thick lips -> increase; thin lips -> decrease
   - "mouth_upperlip_volume": full, thick, plumper upper lip -> increase; thin upper lip -> decrease
   - "mouth_lowerlip_volume": full, thick, plumper lower lip -> increase; thin lower lip -> decrease
   - "mouth_cupids_bow": pronounced, sharp cupid's bow -> increase; flat, subtle cupid's bow -> decrease
   - "philtrum_depth": deep, defined philtrum -> increase; flat, shallow philtrum -> decrease
   - "laugh_lines": deep laugh lines, prominent nasolabial folds -> increase; faint, smooth laugh lines -> decrease
   - "dimples": prominent cheek dimples -> increase; faint, subtle dimples -> decrease
   - "mouth_corner_turn": upturned mouth corners -> increase; downturned mouth corners -> decrease

   Eyes & Eyelids:
   - "eye_size": large, big eyes -> increase; small, narrow eyes -> decrease
   - "eye_spacing": wide-set eyes, eyes far apart -> increase; close-set eyes, eyes closer together -> decrease
   - "eye_tilt": upturned eyes, cat eyes, positive canthal tilt -> increase; downturned eyes, negative canthal tilt -> decrease
   - "hooded_eyelids": hooded eyes, heavy eyelids, prominent eyefolds -> increase; unhooded, open eyelids -> decrease
   - "under_eye_bags": eye bags, puffy eyes, under-eye bags -> increase; smooth under-eyes -> decrease

   Ears:
   - "ear_size": large, big ears -> increase; small, tiny ears -> decrease
   - "ear_protrusion": sticking out ears, protruding ears, winged ears -> increase; flat, pinned ears -> decrease
   - "ear_lobe_size": large earlobes, long earlobes -> increase; small, attached earlobes -> decrease
   - "ear_vertical_length": long, tall ears -> increase; short, compact ears -> decrease

   Jaw, Chin, Cheeks & Brow:
   - "jaw_width": square jaw, broad jaw, chiseled jaw, wide jaw -> increase; narrow, tapered jaw -> decrease
   - "chin_width": broad, wide chin -> increase; narrow, pointed chin -> decrease
   - "chin_prominence": prominent, protruding, jutting chin -> increase; receding, weak chin -> decrease
   - "chin_cleft": cleft chin, dimpled chin -> increase; smooth chin -> decrease
   - "chin_height": tall, long chin -> increase; short chin -> decrease
   - "cheekbone_prominence": prominent, high, sculpted cheekbones -> increase; flat cheekbones -> decrease
   - "cheek_volume": chubby, full cheeks -> increase; hollow, sunken cheeks -> decrease
   - "brow_ridge": prominent brow ridge, heavy brow bone -> increase; flat brow bone -> decrease

2. "direction": MUST be either "increase" or "decrease".

3. "magnitude": MUST be one of:
   - "slight" (slightly, a bit, a little, subtly, mildly, minor, or default change)
   - "moderate" (moderately, medium)
   - "significant" (significantly, much, a lot, considerably, greatly)

4. "assets": Optional array of verified hairstyle or eyebrow styles:
   [{"asset_type": "hair"|"eyebrows", "asset_id": "<id>"}]
   
   Verified Hairstyles ("asset_type": "hair"):
   - "afro01": afro, tight curls, voluminous curls
   - "bob01": classic bob cut, chin-length bob
   - "bob02": textured bob, wavy bob, shaggy bob
   - "braid01": braids, long braided hair, plaits
   - "long01": long straight hair, shoulder-length hair
   - "ponytail01": ponytail, tied back hair
   - "short01": short crop, crew cut, buzz cut
   - "short02": neat side-parted hair, side part
   - "short03": pixie cut, short crop
   - "short04": tousled short hair, messy hair, spiky hair
   - "bald": bald, shaved head, hairless, no hair

   Verified Eyebrow Styles ("asset_type": "eyebrows"):
   - "eyebrow001": natural rounded eyebrows
   - "eyebrow002": straight soft eyebrows
   - "eyebrow003": subtle medium eyebrows
   - "eyebrow004": sharp arched eyebrows
   - "eyebrow005": defined tapered eyebrows
   - "eyebrow006": thin curved eyebrows, pencil thin
   - "eyebrow007": straight eyebrows, flat horizontal
   - "eyebrow008": angled eyebrows, upward angled
   - "eyebrow009": arched eyebrows, high arched
   - "eyebrow010": thick eyebrows, dense eyebrows
   - "eyebrow011": bushy eyebrows, heavy wild eyebrows
   - "eyebrow012": wide full eyebrows, full coverage

CRITICAL FORENSIC RULES:
- If the witness description contains ANY unsupported trait (e.g. hair dye/color like blonde/brunette/red, beard, mustache, goatee, facial hair, skin tone/color, age, gender, race/ethnicity, expressions like smiling/frowning/happy/angry/sad, or ambiguous composite face shapes like diamond/heart), you MUST return:
  {"error": "<explicit explanation of unsupported trait(s)>"}
  Do NOT silently ignore unsupported parts of the description!
- Do not output duplicate or conflicting adjustments for the same feature or asset.
- Only return valid JSON with "features" and/or "assets" (or "error"). Do not include markdown commentary.
"""

FEW_SHOT_EXAMPLES = [
    {
        "role": "user",
        "content": "Make the nose slightly wider."
    },
    {
        "role": "assistant",
        "content": '{"features": [{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}]}'
    },
    {
        "role": "user",
        "content": "Change the hairstyle to a bob cut."
    },
    {
        "role": "assistant",
        "content": '{"features": [], "assets": [{"asset_type": "hair", "asset_id": "bob01"}]}'
    },
    {
        "role": "user",
        "content": "Make the suspect bald with thick eyebrows."
    },
    {
        "role": "assistant",
        "content": '{"features": [], "assets": [{"asset_type": "hair", "asset_id": "bald"}, {"asset_type": "eyebrows", "asset_id": "eyebrow010"}]}'
    },
    {
        "role": "user",
        "content": "A suspect with an afro and a wide jaw."
    },
    {
        "role": "assistant",
        "content": '{"features": [{"feature_id": "jaw_width", "direction": "increase", "magnitude": "slight"}], "assets": [{"asset_type": "hair", "asset_id": "afro01"}]}'
    },
    {
        "role": "user",
        "content": "A person with a neat side-parted haircut, thin curved eyebrows, and prominent cheekbones."
    },
    {
        "role": "assistant",
        "content": '{"features": [{"feature_id": "cheekbone_prominence", "direction": "increase", "magnitude": "slight"}], "assets": [{"asset_type": "hair", "asset_id": "short02"}, {"asset_type": "eyebrows", "asset_id": "eyebrow006"}]}'
    },
    {
        "role": "user",
        "content": "A person with a broad nose, prominent cheekbones, a slightly pointed chin, small eyes, and a narrow face."
    },
    {
        "role": "assistant",
        "content": '{"features": [{"feature_id": "nose_width", "direction": "increase", "magnitude": "slight"}, {"feature_id": "cheekbone_prominence", "direction": "increase", "magnitude": "slight"}, {"feature_id": "chin_width", "direction": "decrease", "magnitude": "slight"}, {"feature_id": "eye_size", "direction": "decrease", "magnitude": "slight"}, {"feature_id": "head_width", "direction": "decrease", "magnitude": "slight"}]}'
    },
    {
        "role": "user",
        "content": "A suspect with full lips, a sharp cupid's bow, and prominent ears."
    },
    {
        "role": "assistant",
        "content": '{"features": [{"feature_id": "mouth_height", "direction": "increase", "magnitude": "slight"}, {"feature_id": "mouth_cupids_bow", "direction": "increase", "magnitude": "slight"}, {"feature_id": "ear_protrusion", "direction": "increase", "magnitude": "slight"}]}'
    },
    {
        "role": "user",
        "content": "A suspect with a dorsal hump on the nose, a square jaw, and hooded eyelids."
    },
    {
        "role": "assistant",
        "content": '{"features": [{"feature_id": "nasal_bridge_hump", "direction": "increase", "magnitude": "slight"}, {"feature_id": "jaw_width", "direction": "increase", "magnitude": "slight"}, {"feature_id": "hooded_eyelids", "direction": "increase", "magnitude": "slight"}]}'
    },
    {
        "role": "user",
        "content": "A suspect with blonde hair, a broad nose, and smiling."
    },
    {
        "role": "assistant",
        "content": '{"error": "Hair color and facial expressions (smiling) are not supported in structural geometry allowlist."}'
    },
    {
        "role": "user",
        "content": "A person with dark skin and large eyes."
    },
    {
        "role": "assistant",
        "content": '{"error": "Skin tone and color modifications are handled via skin tools, not structural geometry allowlist."}'
    },
    {
        "role": "user",
        "content": "Make the nose wider and narrower."
    },
    {
        "role": "assistant",
        "content": '{"error": "Conflicting instructions detected for nose width (both wider and narrower requested)."}'
    }
]


class OllamaRefinementParser:
    def __init__(
        self,
        client: Optional[OllamaClient] = None,
        timeout: Optional[float] = None,
        default_step: float = 0.05
    ):
        if client is not None:
            self.client = client
        elif timeout is not None:
            self.client = OllamaClient(timeout=timeout)
        else:
            self.client = OllamaClient()
        self.default_step = default_step

    def parse(self, text: str) -> ParsedRefinement:
        """
        Parses a natural-language refinement command or multi-feature witness description via Ollama AI.
        Validates model response against the verified allowlist, checks for conflicting/duplicate
        instructions, and returns a structured ParsedRefinement (with .features containing all items).
        """
        if not text or not text.strip():
            raise ParseError("Request text cannot be empty.")

        cleaned = text.strip()
        lower = cleaned.lower()

        # Step 1: Defense-in-depth domain boundary check for unsupported domains
        for pattern, msg in UNSUPPORTED_DOMAINS:
            if re.search(pattern, lower):
                raise ParseError(f"Unsupported request: {msg}")

        # Step 2: Build chat prompt
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(FEW_SHOT_EXAMPLES)
        messages.append({"role": "user", "content": cleaned})

        # Step 3: Call Ollama API
        try:
            response_data = self.client.chat(messages=messages, format="json")
        except OllamaConnectionError as e:
            raise ParseError(f"Ollama connection error: {str(e)}")
        except OllamaTimeoutError as e:
            raise ParseError(f"Ollama timeout error: {str(e)}")
        except OllamaModelNotFoundError as e:
            raise ParseError(f"Ollama model error: {str(e)}")
        except OllamaError as e:
            raise ParseError(f"Ollama error: {str(e)}")
        except Exception as e:
            raise ParseError(f"Unexpected error communicating with Ollama: {str(e)}")

        # Step 4: Extract and clean raw message content
        message_dict = response_data.get("message", {})
        raw_content = message_dict.get("content", "").strip()

        if not raw_content:
            raise ParseError("AI model returned an empty response.")

        # Strip markdown codeblocks if model included them
        if raw_content.startswith("```"):
            raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
            raw_content = re.sub(r"\s*```$", "", raw_content)
            raw_content = raw_content.strip()

        # Step 5: JSON parsing
        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError as initial_err:
            # Fallback: extract embedded JSON object or array if wrapped in conversational text
            json_match = re.search(r'(\{|\[)[^{}\[\]]*(?:(\{|\[)[^{}\[\]]*(\}|\])[^{}\[\]]*)*(\}|\])', raw_content)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    raise ParseError(f"AI parser returned invalid JSON: {str(initial_err)} - Raw output: '{raw_content}'")
            else:
                raise ParseError(f"AI parser returned invalid JSON: {str(initial_err)} - Raw output: '{raw_content}'")

        # Step 6: Validate and extract feature & asset items
        raw_items: List[Dict[str, Any]] = []
        raw_assets: List[Dict[str, Any]] = []

        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            if "error" in data and data["error"]:
                raise ParseError(f"AI parser rejected request: {data['error']}")
            if "features" in data and isinstance(data["features"], list):
                raw_items = data["features"]
            elif "feature_id" in data:
                raw_items = [data]

            if "assets" in data and isinstance(data["assets"], list):
                raw_assets = data["assets"]
            elif "asset_id" in data:
                raw_assets = [data]

            if not raw_items and not raw_assets and "feature_id" not in data and "asset_id" not in data and "features" not in data and "assets" not in data:
                raise ParseError(f"AI parser response must contain a 'features' array or 'assets' array, got: {data}")
        else:
            raise ParseError(f"AI parser response must be a JSON object or array, got {type(data).__name__}.")

        # Parse assets
        parsed_assets: List[ParsedAssetAdjustment] = []
        seen_asset_types: set = set()

        for a_idx, a_item in enumerate(raw_assets):
            if not isinstance(a_item, dict):
                raise ParseError(f"AI parser asset #{a_idx} must be a JSON object, got {type(a_item).__name__}.")
            a_id = str(a_item.get("asset_id", "")).strip().lower()
            a_type = str(a_item.get("asset_type", "")).strip().lower()
            if not a_id:
                raise ParseError(f"AI parser asset #{a_idx} missing 'asset_id'.")
            if not a_type:
                if a_id in HAIRSTYLE_CATALOG:
                    a_type = "hair"
                elif a_id in EYEBROW_CATALOG:
                    a_type = "eyebrows"
                else:
                    raise ParseError(f"AI parser asset #{a_idx} has unknown asset_id '{a_id}'.")

            if a_type not in ("hair", "eyebrows"):
                raise ParseError(f"AI parser asset #{a_idx} has invalid asset_type '{a_type}'. Must be 'hair' or 'eyebrows'.")

            if a_type == "hair":
                if a_id not in HAIRSTYLE_CATALOG:
                    allowed_h = ", ".join(HAIRSTYLE_CATALOG.keys())
                    raise ParseError(f"AI parser proposed unsupported hairstyle '{a_id}'. Allowed hairstyles: [{allowed_h}].")
                asset_def = HAIRSTYLE_CATALOG[a_id]
                action = "remove" if a_id == "bald" else "swap"
            else:
                if a_id not in EYEBROW_CATALOG:
                    allowed_eb = ", ".join(EYEBROW_CATALOG.keys())
                    raise ParseError(f"AI parser proposed unsupported eyebrow style '{a_id}'. Allowed eyebrows: [{allowed_eb}].")
                asset_def = EYEBROW_CATALOG[a_id]
                action = "swap"

            if a_type in seen_asset_types:
                raise ParseError(f"Conflicting or duplicate asset instructions detected for '{a_type}'.")
            seen_asset_types.add(a_type)

            parsed_assets.append(ParsedAssetAdjustment(
                asset_type=a_type,
                asset_id=asset_def.asset_id,
                display_name=asset_def.display_name,
                fragment=asset_def.fragment,
                object_type=asset_def.object_type,
                action=action
            ))

        if not raw_items and not parsed_assets:
            raise ParseError("AI parser did not identify any supported facial features or hairstyles in the description.")

        parsed_items: List[ParsedRefinement] = []
        seen_features: Dict[str, Dict[str, Any]] = {}

        for idx, item in enumerate(raw_items):
            if not isinstance(item, dict):
                raise ParseError(f"AI parser item #{idx} must be a JSON object, got {type(item).__name__}.")

            required_keys = ["feature_id", "direction", "magnitude"]
            missing_keys = [k for k in required_keys if k not in item]
            if missing_keys:
                raise ParseError(f"AI parser item #{idx} missing required field(s): {', '.join(missing_keys)}.")

            # Validate feature_id against allowlist
            raw_fid = str(item["feature_id"]).strip().lower()
            if raw_fid not in VERIFIED_ALLOWLIST:
                allowed = ", ".join(VERIFIED_ALLOWLIST.keys())
                raise ParseError(
                    f"AI parser proposed unsupported feature '{raw_fid}'. "
                    f"Must be one of the verified allowlist: [{allowed}]."
                )
            feature_def: FeatureDefinition = VERIFIED_ALLOWLIST[raw_fid]

            # Validate direction
            raw_dir = str(item["direction"]).strip().lower()
            if raw_dir in ("increase", "widen", "longer", "taller", "larger", "more", "higher", "broad", "broader"):
                direction = 1
            elif raw_dir in ("decrease", "narrow", "shorter", "smaller", "less", "lower", "receding", "pointed", "pointy", "slim", "slimmer"):
                direction = -1
            else:
                raise ParseError(f"AI parser returned invalid direction '{raw_dir}'. Must be 'increase' or 'decrease'.")

            # Validate magnitude
            raw_mag = item["magnitude"]
            if isinstance(raw_mag, (int, float)):
                if 0.0 < raw_mag <= 0.5:
                    magnitude = float(raw_mag)
                else:
                    raise ParseError(f"AI parser returned numerical magnitude {raw_mag} outside supported range (0.01 - 0.50).")
            else:
                mag_str = str(raw_mag).strip().lower()
                if mag_str in ("slight", "slightly", "minor", "small", "a bit", "a little"):
                    magnitude = 0.05
                elif mag_str in ("significant", "significantly", "large", "much", "a lot", "major"):
                    magnitude = 0.10
                elif mag_str in ("moderate", "moderately", "medium"):
                    magnitude = 0.08
                elif mag_str == "default":
                    magnitude = self.default_step
                else:
                    try:
                        num_mag = float(mag_str)
                        if 0.0 < num_mag <= 0.5:
                            magnitude = num_mag
                        else:
                            raise ParseError(f"AI parser returned numerical magnitude {num_mag} outside supported range (0.01 - 0.50).")
                    except ValueError:
                        raise ParseError(
                            f"AI parser returned invalid magnitude '{mag_str}'. "
                            "Must be 'slight', 'moderate', or 'significant'."
                        )

            # Conflict and duplicate check
            if raw_fid in seen_features:
                prev_dir = seen_features[raw_fid]["direction"]
                if direction != prev_dir:
                    raise ParseError(
                        f"Conflicting adjustments detected for feature '{feature_def.display_name}' "
                        f"(both increase and decrease requested). Entire batch rejected."
                    )
                else:
                    raise ParseError(
                        f"Duplicate adjustments detected for feature '{feature_def.display_name}'. "
                        "Please specify a single adjustment per feature. Entire batch rejected."
                    )

            seen_features[raw_fid] = {"direction": direction, "magnitude": magnitude}

            delta = round(direction * magnitude, 4)
            target_shapekey = feature_def.positive_target if direction > 0 else feature_def.negative_target
            target_id = f"{feature_def.section}:{feature_def.category}:{feature_def.side}"

            parsed_items.append(ParsedRefinement(
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
                target_shapekey=target_shapekey
            ))

        # Assemble final result
        if not parsed_items:
            # Asset-only adjustment
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

        if len(parsed_items) == 1:
            single = parsed_items[0]
            single.features = parsed_items
            single.asset_adjustments = parsed_assets if parsed_assets else None
            return single

        # Multi-feature batch result
        all_ids = [p.target_identifier for p in parsed_items]
        all_shapekeys = [p.target_shapekey for p in parsed_items]
        total_delta = round(sum(p.delta for p in parsed_items), 4)

        return ParsedRefinement(
            raw_text=cleaned,
            feature_id="multi_feature",
            display_name=f"Multi-Feature Batch ({len(parsed_items)} features)",
            section="multi",
            category="multi",
            is_sided=any(p.is_sided for p in parsed_items),
            side="multi",
            direction=1,
            magnitude=self.default_step,
            delta=total_delta,
            target_identifier=",".join(all_ids),
            target_shapekey=",".join(all_shapekeys),
            features=parsed_items,
            asset_adjustments=parsed_assets if parsed_assets else None
        )
