"""
Feature Catalog for CrimeSketchAI.

Contains the verified 1-to-1 mapping between the 10 allowlisted facial features
and MPFB target.json categories, sections, sides, and range boundaries.

NOTE ON STATE:
All values in this catalog are CACHED/REFERENCE values based on the verified
baseline from controlled_test_log.json. They are NOT guaranteed live Blender values,
as this system operates in an offline, dry-run mode without live Blender polling.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

@dataclass(frozen=True)
class FeatureDefinition:
    feature_id: str
    display_name: str
    section: str
    category: str
    is_sided: bool
    sides: Tuple[str, ...]
    min_value: float
    max_value: float
    reference_value: float
    adjustment_step: float
    positive_targets: Tuple[str, ...]
    negative_targets: Tuple[str, ...]
    increase_keywords: Tuple[str, ...]
    decrease_keywords: Tuple[str, ...]
    description: str

    @property
    def side(self) -> str:
        """String representation of sides for backward compatibility."""
        return ",".join(self.sides)

    @property
    def baseline_value(self) -> float:
        """Alias for reference_value for backward compatibility."""
        return self.reference_value

    @property
    def positive_target(self) -> str:
        """Primary positive shape key for backward compatibility."""
        return self.positive_targets[0]

    @property
    def negative_target(self) -> str:
        """Primary negative shape key for backward compatibility."""
        return self.negative_targets[0]

    @property
    def target_identifiers(self) -> Tuple[str, ...]:
        """Canonical target identifiers for each side."""
        return tuple(f"{self.section}:{self.category}:{s}" for s in self.sides)


# Verified reference values from the controlled baseline (post nose-width test on 'Human'):
VERIFIED_ALLOWLIST: Dict[str, FeatureDefinition] = {
    "nose_width": FeatureDefinition(
        feature_id="nose_width",
        display_name="nose width",
        section="nose",
        category="nose-scale-horiz-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.20,
        adjustment_step=0.05,
        positive_targets=("nose-scale-horiz-incr",),
        negative_targets=("nose-scale-horiz-decr",),
        increase_keywords=("wider", "broad", "broader", "widen", "large", "larger", "big", "bigger", "increase width", "make wider"),
        decrease_keywords=("narrower", "narrow", "slimmer", "slim", "thin", "thinner", "decrease width", "make narrower", "reduce width"),
        description="Horizontal scaling of the nose."
    ),
    "nose_height": FeatureDefinition(
        feature_id="nose_height",
        display_name="nose height",
        section="nose",
        category="nose-scale-vert-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.05,
        adjustment_step=0.05,
        positive_targets=("nose-scale-vert-incr",),
        negative_targets=("nose-scale-vert-decr",),
        increase_keywords=("longer", "taller", "higher", "increase height", "make longer", "elongate", "lengthen"),
        decrease_keywords=("shorter", "decrease height", "make shorter", "reduce height"),
        description="Vertical scaling/length of the nose."
    ),
    "chin_width": FeatureDefinition(
        feature_id="chin_width",
        display_name="chin width",
        section="chin",
        category="chin-width-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=-0.10,
        adjustment_step=0.05,
        positive_targets=("chin-width-incr",),
        negative_targets=("chin-width-decr",),
        increase_keywords=("wider", "broad", "broader", "widen", "widen chin", "increase width"),
        decrease_keywords=("narrower", "narrow", "pointier", "pointed", "slimmer", "slim", "decrease width", "make narrower"),
        description="Horizontal width of the chin."
    ),
    "chin_prominence": FeatureDefinition(
        feature_id="chin_prominence",
        display_name="chin prominence",
        section="chin",
        category="chin-prominent-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.10,
        adjustment_step=0.05,
        positive_targets=("chin-prominent-incr",),
        negative_targets=("chin-prominent-decr",),
        increase_keywords=("prominent", "more prominent", "forward", "protrude", "protruding", "jut", "jutting", "increase prominence"),
        decrease_keywords=("less prominent", "recede", "receding", "backward", "decrease prominence", "reduce prominence"),
        description="Forward projection / prominence of the chin."
    ),
    "cheekbone_prominence": FeatureDefinition(
        feature_id="cheekbone_prominence",
        display_name="cheekbone prominence",
        section="cheek",
        category="cheek-bones-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.15,
        adjustment_step=0.05,
        positive_targets=("l-cheek-bones-incr", "r-cheek-bones-incr"),
        negative_targets=("l-cheek-bones-decr", "r-cheek-bones-decr"),
        increase_keywords=("prominent", "more prominent", "higher", "pronounced", "sculpted", "sharper", "defined", "increase prominence", "higher cheekbones"),
        decrease_keywords=("less prominent", "flatter", "flat", "lower", "decrease prominence", "reduce prominence"),
        description="Bilateral prominence and definition of cheekbones (left and right)."
    ),
    "eye_size": FeatureDefinition(
        feature_id="eye_size",
        display_name="eye size",
        section="eyes",
        category="eye-scale-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.10,
        adjustment_step=0.05,
        positive_targets=("l-eye-scale-incr", "r-eye-scale-incr"),
        negative_targets=("l-eye-scale-decr", "r-eye-scale-decr"),
        increase_keywords=("larger", "bigger", "large", "big", "enlarge", "increase size", "open", "wider eyes"),
        decrease_keywords=("smaller", "small", "narrower", "decrease size", "reduce size", "shrink"),
        description="Bilateral uniform scaling of the eyes (left and right)."
    ),
    "forehead_size": FeatureDefinition(
        feature_id="forehead_size",
        display_name="forehead size",
        section="forehead",
        category="forehead-scale-vert-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("forehead-scale-vert-incr",),
        negative_targets=("forehead-scale-vert-decr",),
        increase_keywords=("larger", "taller", "higher", "bigger", "increase size", "increase height", "make taller", "larger forehead"),
        decrease_keywords=("smaller", "shorter", "lower", "decrease size", "decrease height", "make shorter", "smaller forehead"),
        description="Vertical height and size of the forehead."
    ),
    "head_width": FeatureDefinition(
        feature_id="head_width",
        display_name="head width",
        section="head",
        category="head-scale-horiz-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=-0.15,
        adjustment_step=0.05,
        positive_targets=("head-scale-horiz-incr",),
        negative_targets=("head-scale-horiz-decr",),
        increase_keywords=("wider", "broad", "broader", "widen", "increase width", "make wider", "wider head"),
        decrease_keywords=("narrower", "narrow", "slimmer", "slim", "decrease width", "make narrower", "narrower head"),
        description="Horizontal scaling of the cranial structure."
    ),
    "head_height": FeatureDefinition(
        feature_id="head_height",
        display_name="head height",
        section="head",
        category="head-scale-vert-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.10,
        adjustment_step=0.05,
        positive_targets=("head-scale-vert-incr",),
        negative_targets=("head-scale-vert-decr",),
        increase_keywords=("taller", "higher", "longer", "increase height", "elongate", "make taller", "taller head"),
        decrease_keywords=("shorter", "lower", "decrease height", "make shorter", "reduce height", "shorter head"),
        description="Vertical scaling of the cranial structure."
    ),
    "mouth_width": FeatureDefinition(
        feature_id="mouth_width",
        display_name="mouth width",
        section="mouth",
        category="mouth-scale-horiz-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=-0.05,
        adjustment_step=0.05,
        positive_targets=("mouth-scale-horiz-incr",),
        negative_targets=("mouth-scale-horiz-decr",),
        increase_keywords=("wider", "broad", "broader", "widen", "increase width", "make wider", "wider mouth"),
        decrease_keywords=("narrower", "narrow", "smaller", "slimmer", "decrease width", "make narrower", "narrower mouth"),
        description="Horizontal width of the mouth."
    ),

    # -------------------------------------------------------------
    # PHASE 1 EXPANSION: 28 NEW VERIFIED FACIAL GEOMETRY CONTROLS
    # -------------------------------------------------------------

    # MOUTH (8 controls)
    "mouth_upperlip_volume": FeatureDefinition(
        feature_id="mouth_upperlip_volume",
        display_name="upper lip volume",
        section="mouth",
        category="mouth-upperlip-volume-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-upperlip-volume-incr",),
        negative_targets=("mouth-upperlip-volume-decr",),
        increase_keywords=("thicker upper lip", "fuller upper lip", "plumper upper lip", "larger upper lip", "increase upper lip", "plump upper lip", "full upper lip"),
        decrease_keywords=("thinner upper lip", "smaller upper lip", "decrease upper lip", "thin upper lip", "reduce upper lip"),
        description="Volume and thickness of the upper lip."
    ),
    "mouth_lowerlip_volume": FeatureDefinition(
        feature_id="mouth_lowerlip_volume",
        display_name="lower lip volume",
        section="mouth",
        category="mouth-lowerlip-volume-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-lowerlip-volume-incr",),
        negative_targets=("mouth-lowerlip-volume-decr",),
        increase_keywords=("thicker lower lip", "fuller lower lip", "plumper lower lip", "larger lower lip", "increase lower lip", "plump lower lip", "full lower lip"),
        decrease_keywords=("thinner lower lip", "smaller lower lip", "decrease lower lip", "thin lower lip", "reduce lower lip"),
        description="Volume and thickness of the lower lip."
    ),
    "mouth_cupids_bow": FeatureDefinition(
        feature_id="mouth_cupids_bow",
        display_name="cupid's bow",
        section="mouth",
        category="mouth-cupidsbow-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-cupidsbow-incr",),
        negative_targets=("mouth-cupidsbow-decr",),
        increase_keywords=("pronounced cupid's bow", "defined cupid's bow", "accentuated cupid's bow", "deeper cupid's bow", "sharper cupid's bow", "cupid's bow"),
        decrease_keywords=("flatter cupid's bow", "less defined cupid's bow", "smooth cupid's bow", "subtle cupid's bow"),
        description="Definition and curvature of the cupid's bow on the upper lip."
    ),
    "philtrum_depth": FeatureDefinition(
        feature_id="philtrum_depth",
        display_name="philtrum depth",
        section="mouth",
        category="mouth-philtrum-volume-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-philtrum-volume-incr",),
        negative_targets=("mouth-philtrum-volume-decr",),
        increase_keywords=("deeper philtrum", "pronounced philtrum", "defined philtrum", "prominent philtrum", "deep philtrum"),
        decrease_keywords=("flatter philtrum", "shallower philtrum", "smooth philtrum", "less defined philtrum", "faint philtrum"),
        description="Depth and definition of the philtrum groove above the upper lip."
    ),
    "laugh_lines": FeatureDefinition(
        feature_id="laugh_lines",
        display_name="laugh lines",
        section="mouth",
        category="mouth-laugh-lines-in-out",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-laugh-lines-out",),
        negative_targets=("mouth-laugh-lines-in",),
        increase_keywords=("prominent laugh lines", "pronounced laugh lines", "deeper laugh lines", "visible laugh lines", "nasolabial folds", "laugh lines", "deeper nasolabial"),
        decrease_keywords=("subtle laugh lines", "reduced laugh lines", "smoother laugh lines", "faint laugh lines", "no laugh lines"),
        description="Nasolabial laugh lines around the mouth."
    ),
    "dimples": FeatureDefinition(
        feature_id="dimples",
        display_name="dimples",
        section="mouth",
        category="mouth-dimples-in-out",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-dimples-out",),
        negative_targets=("mouth-dimples-in",),
        increase_keywords=("prominent dimples", "deep dimples", "deeper dimples", "visible dimples", "dimples", "dimpled cheeks"),
        decrease_keywords=("subtle dimples", "shallower dimples", "faint dimples", "no dimples", "reduced dimples"),
        description="Cheek dimples indentation near the mouth."
    ),
    "mouth_corner_turn": FeatureDefinition(
        feature_id="mouth_corner_turn",
        display_name="mouth corner turn",
        section="mouth",
        category="mouth-angles-down-up",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-angles-up",),
        negative_targets=("mouth-angles-down",),
        increase_keywords=("upturned mouth", "upturned corners", "mouth corners up", "turned up corners", "upturned lips", "corners turned up"),
        decrease_keywords=("downturned mouth", "downturned corners", "mouth corners down", "turned down corners", "downturned lips", "corners turned down"),
        description="Angle and curvature of the mouth corners (upturned vs downturned)."
    ),
    "mouth_height": FeatureDefinition(
        feature_id="mouth_height",
        display_name="mouth height",
        section="mouth",
        category="mouth-scale-vert-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("mouth-scale-vert-incr",),
        negative_targets=("mouth-scale-vert-decr",),
        increase_keywords=("taller mouth", "larger mouth vertically", "higher mouth", "thicker lips", "full lips", "plump lips", "fuller lips", "thicker lips overall"),
        decrease_keywords=("shorter mouth", "smaller mouth vertically", "thinner lips", "thin lips", "thinner lips overall"),
        description="Vertical scale and overall lip thickness."
    ),

    # NOSE (6 controls)
    "nasal_bridge_hump": FeatureDefinition(
        feature_id="nasal_bridge_hump",
        display_name="nasal bridge hump",
        section="nose",
        category="nose-hump-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("nose-hump-incr",),
        negative_targets=("nose-hump-decr",),
        increase_keywords=("dorsal hump", "hump on nose", "hooked nose", "aquiline nose", "prominent nose bridge", "roman nose", "nasal hump", "hump"),
        decrease_keywords=("straight bridge", "smooth bridge", "no hump", "reduced hump", "flatter bridge", "straight nose bridge"),
        description="Dorsal bridge hump / aquiline curvature of the nose."
    ),
    "nasal_bridge_curve": FeatureDefinition(
        feature_id="nasal_bridge_curve",
        display_name="nasal bridge curve",
        section="nose",
        category="nose-curve-concave-convex",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("nose-curve-convex",),
        negative_targets=("nose-curve-concave",),
        increase_keywords=("convex nose", "curved nose", "outward curve", "convex bridge", "convex nasal bridge"),
        decrease_keywords=("concave nose", "scooped nose", "upturned bridge", "celestial nose", "inward curve", "concave bridge", "concave nasal bridge"),
        description="Concave vs convex curvature along the nasal profile."
    ),
    "nostril_width": FeatureDefinition(
        feature_id="nostril_width",
        display_name="nostril width",
        section="nose",
        category="nose-nostrils-width-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("nose-nostrils-width-incr",),
        negative_targets=("nose-nostrils-width-decr",),
        increase_keywords=("flared nostrils", "wider nostrils", "broad nostrils", "large nostrils", "widen nostrils"),
        decrease_keywords=("narrow nostrils", "slender nostrils", "pinched nostrils", "smaller nostrils", "narrower nostrils"),
        description="Width and flare of the nostrils."
    ),
    "nose_tip_width": FeatureDefinition(
        feature_id="nose_tip_width",
        display_name="nose tip width",
        section="nose",
        category="nose-point-width-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("nose-point-width-incr",),
        negative_targets=("nose-point-width-decr",),
        increase_keywords=("bulbous nose", "bulbous tip", "wider nose tip", "broad tip", "round nose tip", "wide tip", "broad nose tip"),
        decrease_keywords=("pointed nose", "pointed tip", "narrow nose tip", "sharp nose tip", "refined tip", "pinched tip", "narrow tip"),
        description="Width and bulbousness of the nasal tip."
    ),
    "nose_tip_angle": FeatureDefinition(
        feature_id="nose_tip_angle",
        display_name="nose tip angle",
        section="nose",
        category="nose-point-down-up",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("nose-point-up",),
        negative_targets=("nose-point-down",),
        increase_keywords=("upturned nose", "snub nose", "pug nose", "tip pointed up", "turned up nose tip", "upturned tip", "elevate nose tip"),
        decrease_keywords=("drooping nose", "droopy nose", "downturned nose", "hooked tip", "pointed down nose tip", "downturned tip", "drooping tip"),
        description="Vertical angle of the nasal tip (upturned vs drooping)."
    ),
    "nose_projection": FeatureDefinition(
        feature_id="nose_projection",
        display_name="nose projection",
        section="nose",
        category="nose-scale-depth-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("nose-scale-depth-incr",),
        negative_targets=("nose-scale-depth-decr",),
        increase_keywords=("protruding nose", "prominent nose", "projecting nose", "longer nose depth", "deep nose", "more projecting nose"),
        decrease_keywords=("flat nose", "receding nose", "shallow nose", "less projecting nose", "flatter nose profile"),
        description="Forward projection / depth of the nose from the face plane."
    ),

    # EARS (4 controls, bilateral)
    "ear_size": FeatureDefinition(
        feature_id="ear_size",
        display_name="ear size",
        section="ears",
        category="ear-scale-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-ear-scale-incr", "r-ear-scale-incr"),
        negative_targets=("l-ear-scale-decr", "r-ear-scale-decr"),
        increase_keywords=("large ears", "larger ears", "big ears", "bigger ears", "enlarge ears", "increase ear size"),
        decrease_keywords=("small ears", "smaller ears", "tiny ears", "reduce ears", "decrease ear size"),
        description="Bilateral uniform scaling of the ears."
    ),
    "ear_protrusion": FeatureDefinition(
        feature_id="ear_protrusion",
        display_name="ear protrusion",
        section="ears",
        category="ear-wing-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-ear-wing-incr", "r-ear-wing-incr"),
        negative_targets=("l-ear-wing-decr", "r-ear-wing-decr"),
        increase_keywords=("sticking out ears", "protruding ears", "prominent ears", "flared ears", "ears stick out", "winged ears", "ear flare"),
        decrease_keywords=("flat ears", "pinned back ears", "ears close to head", "less protruding ears", "pinned ears"),
        description="Bilateral winging / protrusion of the ears away from the skull."
    ),
    "ear_lobe_size": FeatureDefinition(
        feature_id="ear_lobe_size",
        display_name="ear lobe size",
        section="ears",
        category="ear-lobe-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-ear-lobe-incr", "r-ear-lobe-incr"),
        negative_targets=("l-ear-lobe-decr", "r-ear-lobe-decr"),
        increase_keywords=("large earlobes", "larger earlobes", "long earlobes", "hanging earlobes", "big earlobes", "enlarge earlobes"),
        decrease_keywords=("small earlobes", "smaller earlobes", "attached earlobes", "tiny earlobes", "reduce earlobes"),
        description="Bilateral sizing and length of the earlobes."
    ),
    "ear_vertical_length": FeatureDefinition(
        feature_id="ear_vertical_length",
        display_name="ear length",
        section="ears",
        category="ear-scale-vert-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-ear-scale-vert-incr", "r-ear-scale-vert-incr"),
        negative_targets=("l-ear-scale-vert-decr", "r-ear-scale-vert-decr"),
        increase_keywords=("longer ears", "tall ears", "elongated ears", "increase ear length"),
        decrease_keywords=("shorter ears", "compact ears", "reduce ear length", "decrease ear length"),
        description="Bilateral vertical length of the ears."
    ),

    # EYES & EYELIDS (4 controls, bilateral)
    "eye_spacing": FeatureDefinition(
        feature_id="eye_spacing",
        display_name="eye spacing",
        section="eyes",
        category="eye-trans-in-out",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-eye-trans-out", "r-eye-trans-out"),
        negative_targets=("l-eye-trans-in", "r-eye-trans-in"),
        increase_keywords=("wide-set eyes", "wide set eyes", "far apart eyes", "eyes wider apart", "spaced out eyes", "wider eye spacing"),
        decrease_keywords=("close-set eyes", "close set eyes", "eyes closer together", "narrow set eyes", "narrow eye spacing"),
        description="Bilateral horizontal translation / spacing between the eyes."
    ),
    "eye_tilt": FeatureDefinition(
        feature_id="eye_tilt",
        display_name="eye tilt",
        section="eyes",
        category="eye-corner2-down-up",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-eye-corner2-up", "r-eye-corner2-up"),
        negative_targets=("l-eye-corner2-down", "r-eye-corner2-down"),
        increase_keywords=("upturned eyes", "cat eyes", "slanted eyes", "canthal tilt up", "positive canthal tilt", "upturned eye corners"),
        decrease_keywords=("downturned eyes", "canthal tilt down", "negative canthal tilt", "drooping eye corners", "downturned eye corners"),
        description="Bilateral canthal tilt / angle of the outer eye corners."
    ),
    "hooded_eyelids": FeatureDefinition(
        feature_id="hooded_eyelids",
        display_name="hooded eyelids",
        section="eyes",
        category="eye-eyefold-concave-convex",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-eye-eyefold-convex", "r-eye-eyefold-convex"),
        negative_targets=("l-eye-eyefold-concave", "r-eye-eyefold-concave"),
        increase_keywords=("hooded eyes", "hooded eyelids", "heavy eyelids", "prominent eyefolds", "epicanthic fold", "more hooded eyelids"),
        decrease_keywords=("unhooded eyes", "deep-set eyes", "defined crease", "open eyelids", "less hooded eyelids"),
        description="Bilateral convex eyefold hooding over the upper eyelid."
    ),
    "under_eye_bags": FeatureDefinition(
        feature_id="under_eye_bags",
        display_name="under eye bags",
        section="eyes",
        category="eye-bag-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-eye-bag-incr", "r-eye-bag-incr"),
        negative_targets=("l-eye-bag-decr", "r-eye-bag-decr"),
        increase_keywords=("eye bags", "under eye bags", "puffy eyes", "bags under eyes", "tired eyes", "puffy under eyes"),
        decrease_keywords=("smooth under eyes", "no eye bags", "reduced eye bags", "faint eye bags", "less eye bags"),
        description="Bilateral puffiness and bags beneath the lower eyelids."
    ),

    # JAW & CHIN (3 controls, unsided)
    "jaw_width": FeatureDefinition(
        feature_id="jaw_width",
        display_name="jaw width",
        section="chin",
        category="chin-jaw-drop-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("chin-jaw-drop-incr",),
        negative_targets=("chin-jaw-drop-decr",),
        increase_keywords=("square jaw", "broad jaw", "wide jaw", "wider jaw", "chiseled jaw", "heavy jaw", "widen jaw"),
        decrease_keywords=("narrow jaw", "narrower jaw", "tapered jaw", "soft jaw", "slender jaw", "narrow jawline"),
        description="Width and angular drop of the mandibular jawline."
    ),
    "chin_cleft": FeatureDefinition(
        feature_id="chin_cleft",
        display_name="chin cleft",
        section="chin",
        category="chin-cleft-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("chin-cleft-incr",),
        negative_targets=("chin-cleft-decr",),
        increase_keywords=("cleft chin", "dimpled chin", "chin cleft", "cleft in chin", "split chin", "prominent chin cleft"),
        decrease_keywords=("smooth chin", "no cleft", "un-cleft chin", "reduced chin cleft", "less cleft chin"),
        description="Cleft or dimple indentation in the center of the chin."
    ),
    "chin_height": FeatureDefinition(
        feature_id="chin_height",
        display_name="chin height",
        section="chin",
        category="chin-height-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("chin-height-incr",),
        negative_targets=("chin-height-decr",),
        increase_keywords=("longer chin", "tall chin", "taller chin", "extended chin", "long chin", "increase chin height"),
        decrease_keywords=("shorter chin", "compact chin", "reduced chin height", "short chin", "decrease chin height"),
        description="Vertical length and height of the chin."
    ),

    # SUPPLEMENTARY CONTROLS (3 controls)
    "cheek_volume": FeatureDefinition(
        feature_id="cheek_volume",
        display_name="cheek volume",
        section="cheek",
        category="cheek-volume-decr-incr",
        is_sided=True,
        sides=("left", "right"),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("l-cheek-volume-incr", "r-cheek-volume-incr"),
        negative_targets=("l-cheek-volume-decr", "r-cheek-volume-decr"),
        increase_keywords=("chubby cheeks", "full cheeks", "puffy cheeks", "buccal fullness", "fuller cheeks", "increase cheek volume"),
        decrease_keywords=("hollow cheeks", "sunken cheeks", "gaunt cheeks", "slimmer cheeks", "reduce cheek volume"),
        description="Bilateral cheek volume and buccal fullness."
    ),
    "temple_width": FeatureDefinition(
        feature_id="temple_width",
        display_name="temple width",
        section="forehead",
        category="forehead-temple-decr-incr",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("forehead-temple-incr",),
        negative_targets=("forehead-temple-decr",),
        increase_keywords=("wider temples", "broad temples", "widen temples", "increase temple width"),
        decrease_keywords=("narrower temples", "narrow temples", "pinched temples", "reduce temple width"),
        description="Width across the temporal region of the forehead."
    ),
    "brow_ridge": FeatureDefinition(
        feature_id="brow_ridge",
        display_name="brow ridge",
        section="eyebrows",
        category="eyebrows-trans-backward-forward",
        is_sided=False,
        sides=("unsided",),
        min_value=-1.0,
        max_value=1.0,
        reference_value=0.00,
        adjustment_step=0.05,
        positive_targets=("eyebrows-trans-forward",),
        negative_targets=("eyebrows-trans-backward",),
        increase_keywords=("prominent brow ridge", "heavy brow", "protruding brow bone", "pronounced brow", "forward brow", "prominent brow bone"),
        decrease_keywords=("flat brow ridge", "receding brow bone", "smooth brow", "flatter brow"),
        description="Forward protrusion of the supraorbital brow ridge."
    ),
}
