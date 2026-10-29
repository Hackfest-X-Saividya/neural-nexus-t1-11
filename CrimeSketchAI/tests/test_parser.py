"""
Unit tests for CrimeSketchAI RefinementParser.
"""

import pytest
from backend.parser.refinement_parser import RefinementParser, ParseError
from backend.parser.feature_catalog import VERIFIED_ALLOWLIST

@pytest.fixture
def parser():
    return RefinementParser(default_step=0.05)

class TestSupportedFeatures:
    def test_nose_width_increase(self, parser):
        res = parser.parse("Make the nose slightly wider.")
        assert res.feature_id == "nose_width"
        assert res.section == "nose"
        assert res.category == "nose-scale-horiz-decr-incr"
        assert res.direction == 1
        assert res.magnitude == 0.05
        assert res.delta == 0.05
        assert res.target_identifier == "nose:nose-scale-horiz-decr-incr:unsided"
        assert res.target_shapekey == "nose-scale-horiz-incr"

    def test_nose_width_decrease(self, parser):
        res = parser.parse("Make the nose narrower.")
        assert res.feature_id == "nose_width"
        assert res.direction == -1
        assert res.delta == -0.05
        assert res.target_shapekey == "nose-scale-horiz-decr"

    def test_nose_height_increase(self, parser):
        res = parser.parse("Make the nose longer.")
        assert res.feature_id == "nose_height"
        assert res.category == "nose-scale-vert-decr-incr"
        assert res.direction == 1
        assert res.delta == 0.05

    def test_nose_height_decrease(self, parser):
        res = parser.parse("Make the nose slightly shorter.")
        assert res.feature_id == "nose_height"
        assert res.direction == -1
        assert res.delta == -0.05

    def test_chin_width(self, parser):
        res_w = parser.parse("Make the chin wider.")
        assert res_w.feature_id == "chin_width"
        assert res_w.direction == 1
        
        res_n = parser.parse("Make the chin narrower.")
        assert res_n.feature_id == "chin_width"
        assert res_n.direction == -1

    def test_chin_prominence(self, parser):
        res_inc1 = parser.parse("Increase the chin prominence slightly.")
        assert res_inc1.feature_id == "chin_prominence"
        assert res_inc1.category == "chin-prominent-decr-incr"
        assert res_inc1.direction == 1
        assert res_inc1.delta == 0.05

        res_inc2 = parser.parse("Make the chin more prominent slightly.")
        assert res_inc2.feature_id == "chin_prominence"
        assert res_inc2.direction == 1

        res_dec = parser.parse("Make the chin less prominent.")
        assert res_dec.feature_id == "chin_prominence"
        assert res_dec.direction == -1

    def test_cheekbone_prominence(self, parser):
        res = parser.parse("Make the cheekbones more prominent.")
        assert res.feature_id == "cheekbone_prominence"
        assert res.category == "cheek-bones-decr-incr"
        assert res.is_sided is True
        assert res.direction == 1

        res_flat = parser.parse("Make the cheekbones flatter.")
        assert res_flat.feature_id == "cheekbone_prominence"
        assert res_flat.direction == -1

    def test_eye_size(self, parser):
        res_lg = parser.parse("Make the eyes slightly larger.")
        assert res_lg.feature_id == "eye_size"
        assert res_lg.category == "eye-scale-decr-incr"
        assert res_lg.is_sided is True
        assert res_lg.direction == 1
        assert res_lg.delta == 0.05

        res_sm = parser.parse("Make the eyes smaller.")
        assert res_sm.feature_id == "eye_size"
        assert res_sm.direction == -1

    def test_forehead_size(self, parser):
        res_t = parser.parse("Make the forehead taller.")
        assert res_t.feature_id == "forehead_size"
        assert res_t.category == "forehead-scale-vert-decr-incr"
        assert res_t.direction == 1

        res_s = parser.parse("Make the forehead smaller.")
        assert res_s.feature_id == "forehead_size"
        assert res_s.direction == -1

    def test_head_width(self, parser):
        res = parser.parse("Make the head wider.")
        assert res.feature_id == "head_width"
        assert res.category == "head-scale-horiz-decr-incr"
        assert res.direction == 1

        res_n = parser.parse("Make the head narrower.")
        assert res_n.feature_id == "head_width"
        assert res_n.direction == -1

    def test_head_height(self, parser):
        res = parser.parse("Make the head taller.")
        assert res.feature_id == "head_height"
        assert res.category == "head-scale-vert-decr-incr"
        assert res.direction == 1

        res_s = parser.parse("Make the head shorter.")
        assert res_s.feature_id == "head_height"
        assert res_s.direction == -1

    def test_mouth_width(self, parser):
        res = parser.parse("Make the mouth wider.")
        assert res.feature_id == "mouth_width"
        assert res.category == "mouth-scale-horiz-decr-incr"
        assert res.direction == 1

        res_n = parser.parse("Make the mouth narrower.")
        assert res_n.feature_id == "mouth_width"
        assert res_n.direction == -1

    def test_mouth_expansion_controls(self, parser):
        # Upper lip volume
        res_ul = parser.parse("Make the upper lip fuller.")
        assert res_ul.feature_id == "mouth_upperlip_volume"
        assert res_ul.direction == 1
        assert res_ul.target_shapekey == "mouth-upperlip-volume-incr"

        res_ul_thin = parser.parse("Make the upper lip thinner.")
        assert res_ul_thin.feature_id == "mouth_upperlip_volume"
        assert res_ul_thin.direction == -1
        assert res_ul_thin.target_shapekey == "mouth-upperlip-volume-decr"

        # Lower lip volume
        res_ll = parser.parse("Make the lower lip fuller.")
        assert res_ll.feature_id == "mouth_lowerlip_volume"
        assert res_ll.direction == 1

        # Cupid's bow
        res_cb = parser.parse("Make the cupid's bow more defined.")
        assert res_cb.feature_id == "mouth_cupids_bow"
        assert res_cb.direction == 1
        assert res_cb.target_shapekey == "mouth-cupidsbow-incr"

        # Philtrum depth
        res_ph = parser.parse("Make the philtrum deeper.")
        assert res_ph.feature_id == "philtrum_depth"
        assert res_ph.direction == 1

        # Laugh lines
        res_llines = parser.parse("Make the laugh lines deeper.")
        assert res_llines.feature_id == "laugh_lines"
        assert res_llines.direction == 1

        # Dimples
        res_dimp = parser.parse("Make the dimples deeper.")
        assert res_dimp.feature_id == "dimples"
        assert res_dimp.direction == 1

        # Mouth corner turn
        res_ct_up = parser.parse("Make the mouth corners upturned.")
        assert res_ct_up.feature_id == "mouth_corner_turn"
        assert res_ct_up.direction == 1
        assert res_ct_up.target_shapekey == "mouth-angles-up"

        res_ct_down = parser.parse("Make the mouth corners downturned.")
        assert res_ct_down.feature_id == "mouth_corner_turn"
        assert res_ct_down.direction == -1
        assert res_ct_down.target_shapekey == "mouth-angles-down"

        # Mouth height / lip fullness
        res_full = parser.parse("Make the lips fuller.")
        assert res_full.feature_id == "mouth_height"
        assert res_full.direction == 1

    def test_nose_expansion_controls(self, parser):
        # Nasal bridge hump
        res_hump = parser.parse("Give him a dorsal hump on the nose.")
        assert res_hump.feature_id == "nasal_bridge_hump"
        assert res_hump.direction == 1
        assert res_hump.target_shapekey == "nose-hump-incr"

        res_hooked = parser.parse("Give him a hooked nose.")
        assert res_hooked.feature_id == "nasal_bridge_hump"
        assert res_hooked.direction == 1

        # Nasal bridge curve
        res_curve = parser.parse("Make the nose bridge convex.")
        assert res_curve.feature_id == "nasal_bridge_curve"
        assert res_curve.direction == 1

        # Nostril width
        res_nost = parser.parse("Make the nostrils flared.")
        assert res_nost.feature_id == "nostril_width"
        assert res_nost.direction == 1
        assert res_nost.target_shapekey == "nose-nostrils-width-incr"

        # Nose tip width
        res_tip_w = parser.parse("Make the nose tip bulbous.")
        assert res_tip_w.feature_id == "nose_tip_width"
        assert res_tip_w.direction == 1

        # Nose tip angle
        res_snub = parser.parse("Make the nose snub.")
        assert res_snub.feature_id == "nose_tip_angle"
        assert res_snub.direction == 1

        # Nose projection
        res_proj = parser.parse("Make the nose more protruding.")
        assert res_proj.feature_id == "nose_projection"
        assert res_proj.direction == 1

    def test_ears_expansion_controls(self, parser):
        # Ear size (bilateral)
        res_es = parser.parse("Make the ears larger.")
        assert res_es.feature_id == "ear_size"
        assert res_es.is_sided is True
        assert res_es.direction == 1
        assert res_es.target_shapekey == "l-ear-scale-incr"

        # Ear protrusion (bilateral)
        res_ep = parser.parse("Make the ears stick out more.")
        assert res_ep.feature_id == "ear_protrusion"
        assert res_ep.is_sided is True
        assert res_ep.direction == 1
        assert res_ep.target_shapekey == "l-ear-wing-incr"

        # Ear lobe size (bilateral)
        res_el = parser.parse("Make the earlobes larger.")
        assert res_el.feature_id == "ear_lobe_size"
        assert res_el.is_sided is True
        assert res_el.direction == 1

        # Ear length (bilateral)
        res_elen = parser.parse("Make the ears longer.")
        assert res_elen.feature_id == "ear_vertical_length"
        assert res_elen.is_sided is True
        assert res_elen.direction == 1

    def test_eyes_expansion_controls(self, parser):
        # Eye spacing (bilateral)
        res_sp = parser.parse("Make the eyes wide-set.")
        assert res_sp.feature_id == "eye_spacing"
        assert res_sp.is_sided is True
        assert res_sp.direction == 1

        # Eye tilt (bilateral)
        res_tilt = parser.parse("Make the eyes upturned.")
        assert res_tilt.feature_id == "eye_tilt"
        assert res_tilt.is_sided is True
        assert res_tilt.direction == 1

        # Hooded eyelids (bilateral)
        res_hood = parser.parse("Make the eyelids hooded.")
        assert res_hood.feature_id == "hooded_eyelids"
        assert res_hood.is_sided is True
        assert res_hood.direction == 1
        assert res_hood.target_shapekey == "l-eye-eyefold-convex"

        # Under eye bags (bilateral)
        res_bags = parser.parse("Give him eye bags.")
        assert res_bags.feature_id == "under_eye_bags"
        assert res_bags.is_sided is True
        assert res_bags.direction == 1
        assert res_bags.target_shapekey == "l-eye-bag-incr"

    def test_chin_jaw_expansion_controls(self, parser):
        # Jaw width
        res_jaw = parser.parse("Make the jaw wider.")
        assert res_jaw.feature_id == "jaw_width"
        assert res_jaw.direction == 1
        assert res_jaw.target_shapekey == "chin-jaw-drop-incr"

        # Chin cleft
        res_cleft = parser.parse("Add a cleft chin.")
        assert res_cleft.feature_id == "chin_cleft"
        assert res_cleft.direction == 1
        assert res_cleft.target_shapekey == "chin-cleft-incr"

        # Chin height
        res_ch = parser.parse("Make the chin taller.")
        assert res_ch.feature_id == "chin_height"
        assert res_ch.direction == 1

    def test_supplementary_expansion_controls(self, parser):
        # Cheek volume (bilateral)
        res_cv = parser.parse("Make the cheeks chubby.")
        assert res_cv.feature_id == "cheek_volume"
        assert res_cv.is_sided is True
        assert res_cv.direction == 1

        # Temple width
        res_tw = parser.parse("Make the temples wider.")
        assert res_tw.feature_id == "temple_width"
        assert res_tw.direction == 1

        # Brow ridge
        res_br = parser.parse("Make the brow ridge more prominent.")
        assert res_br.feature_id == "brow_ridge"
        assert res_br.direction == 1

class TestMagnitudeHandling:
    def test_slightly_magnitude(self, parser):
        res = parser.parse("Make the nose slightly wider.")
        assert res.magnitude == 0.05
        assert res.delta == 0.05

    def test_significantly_magnitude(self, parser):
        res = parser.parse("Make the nose significantly wider.")
        assert res.magnitude == 0.10
        assert res.delta == 0.10

    def test_default_magnitude(self, parser):
        res = parser.parse("Make the nose wider.")
        assert res.magnitude == 0.05
        assert res.delta == 0.05

class TestAmbiguousAndUnsupportedInputs:
    def test_empty_string(self, parser):
        with pytest.raises(ParseError, match="cannot be empty"):
            parser.parse("")

    def test_multiple_commands_rejected(self, parser):
        with pytest.raises(ParseError, match="Multiple compound instructions"):
            parser.parse("Make the nose wider and make the eyes larger.")

    def test_unsupported_hair(self, parser):
        with pytest.raises(ParseError, match="Hair modifications are not supported"):
            parser.parse("Make the hair longer.")

    def test_unsupported_skin(self, parser):
        with pytest.raises(ParseError, match="Skin material/tone modifications are handled via skin tools"):
            parser.parse("Change the skin color.")

    def test_unsupported_expression(self, parser):
        with pytest.raises(ParseError, match="Smiling is an expression unit"):
            parser.parse("Make the suspect smile.")

    def test_ambiguous_nose_instruction(self, parser):
        with pytest.raises(ParseError, match="Ambiguous nose instruction"):
            parser.parse("Change the nose.")

    def test_ambiguous_chin_instruction(self, parser):
        with pytest.raises(ParseError, match="Ambiguous chin instruction"):
            parser.parse("Adjust the chin.")

    def test_conflicting_directions(self, parser):
        with pytest.raises(ParseError, match="Conflicting directions detected"):
            parser.parse("Make the nose wider narrower.")


class TestAssetParsing:
    def test_pure_hairstyle_swap(self, parser):
        res = parser.parse("Change the hairstyle to a bob cut.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        adj = res.asset_adjustments[0]
        assert adj.asset_type == "hair"
        assert adj.asset_id == "bob01"
        assert adj.display_name == "Bob Cut"
        assert adj.fragment == "bob01/bob01.mhclo"
        assert adj.action == "swap"

    def test_pure_bald_request(self, parser):
        res = parser.parse("Make the suspect bald.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        adj = res.asset_adjustments[0]
        assert adj.asset_type == "hair"
        assert adj.asset_id == "bald"
        assert adj.display_name == "Bald"
        assert adj.fragment is None
        assert adj.action == "remove"

    def test_pure_eyebrow_swap(self, parser):
        res = parser.parse("Thin curved eyebrows.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        adj = res.asset_adjustments[0]
        assert adj.asset_type == "eyebrows"
        assert adj.asset_id == "eyebrow006"
        assert adj.display_name == "Thin Curved Eyebrows"
        assert adj.fragment == "eyebrow006/eyebrow006.mhclo"
        assert adj.action == "swap"

    def test_hair_and_eyebrow_combined(self, parser):
        res = parser.parse("Make the suspect bald with thick eyebrows.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 2
        types = {a.asset_type: a for a in res.asset_adjustments}
        assert types["hair"].asset_id == "bald"
        assert types["eyebrows"].asset_id == "eyebrow010"

    def test_hair_and_geometry_combined(self, parser):
        res = parser.parse("A suspect with an afro and a wide jaw.")
        assert res.feature_id == "jaw_width"
        assert res.direction == 1
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        assert res.asset_adjustments[0].asset_id == "afro01"

    def test_hair_eyebrows_and_geometry_combined(self, parser):
        res = parser.parse("A person with a neat side-parted haircut, thin curved eyebrows, and prominent cheekbones.")
        assert res.feature_id == "cheekbone_prominence"
        assert res.direction == 1
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 2
        types = {a.asset_type: a for a in res.asset_adjustments}
        assert types["hair"].asset_id == "short02"
        assert types["eyebrows"].asset_id == "eyebrow006"

    def test_conflicting_hairstyles_rejected(self, parser):
        with pytest.raises(ParseError, match="Conflicting hairstyle instructions"):
            parser.parse("Give him an afro and a bob cut.")

    def test_conflicting_eyebrows_rejected(self, parser):
        with pytest.raises(ParseError, match="Conflicting eyebrow instructions"):
            parser.parse("Give him thin eyebrows and thick eyebrows.")

    def test_hair_dye_rejected(self, parser):
        with pytest.raises(ParseError, match="Hair color and dye modifications are not supported"):
            parser.parse("A suspect with blonde hair.")

    def test_beard_rejected(self, parser):
        with pytest.raises(ParseError, match="Beard and facial hair are not supported"):
            parser.parse("A suspect with a beard and an afro.")


class TestCurlyHairstylesAndAllowlistEnforcement:
    def test_curly_hair_maps_to_afro01(self, parser):
        res = parser.parse("The suspect has curly hair.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        adj = res.asset_adjustments[0]
        assert adj.asset_id == "afro01"
        assert adj.display_name == "Afro"
        assert adj.fragment == "afro01/afro01.mhclo"
        assert adj.action == "swap"

    def test_short_curly_hair_maps_to_afro01(self, parser):
        res = parser.parse("A suspect with short curly hair.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments[0].asset_id == "afro01"

    def test_tight_curls_maps_to_afro01(self, parser):
        res = parser.parse("The suspect had tight curls.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments[0].asset_id == "afro01"

    def test_loose_curls_maps_to_bob02(self, parser):
        res = parser.parse("She had loose curls.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        adj = res.asset_adjustments[0]
        assert adj.asset_id == "bob02"
        assert adj.display_name == "Textured Bob"
        assert adj.fragment == "bob02/bob02.mhclo"

    def test_long_curly_hair_maps_to_long01(self, parser):
        res = parser.parse("The witness described long curly hair.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        adj = res.asset_adjustments[0]
        assert adj.asset_id == "long01"
        assert adj.display_name == "Long Hair"
        assert adj.fragment == "long01/long01.mhclo"

    def test_make_the_hair_curly(self, parser):
        res = parser.parse("Make the hair curly.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments[0].asset_id == "afro01"

    def test_the_suspect_has_curls(self, parser):
        res = parser.parse("The suspect has curls.")
        assert res.feature_id == "asset_customization"
        assert res.asset_adjustments[0].asset_id == "afro01"

    def test_curly_hair_and_geometry_combined(self, parser):
        res = parser.parse("A suspect with curly hair and a wide jaw.")
        assert res.feature_id == "jaw_width"
        assert res.direction == 1
        assert res.asset_adjustments is not None
        assert len(res.asset_adjustments) == 1
        assert res.asset_adjustments[0].asset_id == "afro01"

    def test_loose_curls_and_eyebrows_combined(self, parser):
        res = parser.parse("A person with loose curls and thin curved eyebrows.")
        assert res.feature_id == "asset_customization"
        assert len(res.asset_adjustments) == 2
        types = {a.asset_type: a for a in res.asset_adjustments}
        assert types["hair"].asset_id == "bob02"
        assert types["eyebrows"].asset_id == "eyebrow006"

    def test_unsupported_hairstyle_dreadlocks_rejected_with_supported_list(self, parser):
        with pytest.raises(ParseError) as exc_info:
            parser.parse("The suspect has dreadlocks.")
        msg = str(exc_info.value)
        assert "Hair modifications are not supported" in msg
        assert "dreadlocks" in msg
        assert "Supported hairstyles:" in msg
        assert "afro01" in msg
        assert "bob02" in msg

    def test_unsupported_hairstyle_mohawk_rejected_with_supported_list(self, parser):
        with pytest.raises(ParseError) as exc_info:
            parser.parse("Give the suspect a mohawk.")
        msg = str(exc_info.value)
        assert "Hair modifications are not supported" in msg
        assert "mohawk" in msg
        assert "Supported hairstyles:" in msg

    def test_arbitrary_hair_name_rejected(self, parser):
        with pytest.raises(ParseError) as exc_info:
            parser.parse("Change hair to futuristic_cyber_hair.")
        msg = str(exc_info.value)
        assert "Hair modifications are not supported" in msg
        assert "Supported hairstyles:" in msg


