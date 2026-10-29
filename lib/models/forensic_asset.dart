class ForensicAsset {
  final String slot; // 'hair', 'eyebrows', 'eyelashes', 'glasses', 'moustache', 'beard', 'nose', 'ears', 'skin', 'eyes'
  final String id;
  final String name;
  final String description;
  final String? thumb;
  final String? obj;
  final String? texture;
  final String? target;
  final String license;

  const ForensicAsset({
    required this.slot,
    required this.id,
    required this.name,
    required this.description,
    this.thumb,
    this.obj,
    this.texture,
    this.target,
    this.license = 'CC0 (Public Domain - MakeHuman)',
  });
}

class AssetCatalog {
  // 1. BEARDS (Real MakeHuman OBJ Meshes + Textures)
  static const List<ForensicAsset> beardAssets = [
    ForensicAsset(
      slot: 'beard',
      id: 'beard_viking',
      name: 'Viking Beard',
      description: 'Full Nordic braided beard with textured grooming',
      thumb: 'models/bodyparts05_cc0/clothes/rehmanpolanski_beard_viking/rehmanpolanski_beard_viking.png',
      obj: 'models/bodyparts05_cc0/clothes/rehmanpolanski_beard_viking/beardviking.obj',
      texture: 'models/bodyparts05_cc0/clothes/rehmanpolanski_beard_viking/BeardViking.png',
      license: 'CC0 - Rehman Polanski',
    ),
    ForensicAsset(
      slot: 'beard',
      id: 'scruffy_beard',
      name: 'Scruffy Beard',
      description: 'Natural rugged medium scruff beard',
      thumb: 'models/bodyparts05_cc0/clothes/wdg_scruffy_beard/wdg_scruffy_beard.png',
      obj: 'models/bodyparts05_cc0/clothes/wdg_scruffy_beard/scruffy_beard.obj',
      texture: 'models/bodyparts05_cc0/clothes/wdg_scruffy_beard/beard2_texture-SMUDGE2.png',
      license: 'CC0 - WDG',
    ),
    ForensicAsset(
      slot: 'beard',
      id: 'faun_beard',
      name: 'Faun Beard',
      description: 'Chiseled pointed chin beard',
      thumb: 'models/bodyparts05_cc0/clothes/culturalibre_faun_beard/culturalibre_faun_beard.png',
      obj: 'models/bodyparts05_cc0/clothes/culturalibre_faun_beard/faun_beard.obj',
      texture: 'models/bodyparts05_cc0/clothes/culturalibre_faun_beard/brown.png',
      license: 'CC0 - culturalibre',
    ),
    ForensicAsset(
      slot: 'beard',
      id: 'beard_sigmund',
      name: 'Sigmund Beard',
      description: 'Classic full academic beard and sideburns',
      thumb: 'models/bodyparts05_cc0/clothes/grinsegold_beard_sigmund_wip/grinsegold_beard_sigmund_wip.png',
      obj: 'models/bodyparts05_cc0/clothes/grinsegold_beard_sigmund_wip/beard_sigmund.obj',
      license: 'CC0 - grinsegold',
    ),
  ];

  // 2. MOUSTACHE (Real MakeHuman OBJ Mesh + Texture)
  static const List<ForensicAsset> moustacheAssets = [
    ForensicAsset(
      slot: 'moustache',
      id: 'moustache_viking',
      name: 'Viking Moustache',
      description: 'Prominent trimmed upper lip moustache',
      thumb: 'models/bodyparts05_cc0/clothes/rehmanpolanski_moustache_viking/rehmanpolanski_moustache_viking.png',
      obj: 'models/bodyparts05_cc0/clothes/rehmanpolanski_moustache_viking/moustacheviking.obj',
      texture: 'models/bodyparts05_cc0/clothes/rehmanpolanski_moustache_viking/MoustacheViking.png',
      license: 'CC0 - Rehman Polanski',
    ),
    ForensicAsset(
      slot: 'moustache',
      id: 'classic',
      name: 'Classic Trim',
      description: 'Trimmed pencil moustache above upper lip',
      license: 'Built-in Procedural',
    ),
  ];

  // 3. EYEBROWS (Real MakeHuman OBJ Meshes)
  static const List<ForensicAsset> eyebrowAssets = [
    ForensicAsset(
      slot: 'eyebrows',
      id: 'mindfront_eyebrows_01',
      name: 'Brow Style #01',
      description: 'Natural arch 3D brow mesh',
      thumb: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_01/mindfront_eyebrows_01.png',
      obj: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_01/mind_eyebrows_01.obj',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'eyebrows',
      id: 'mindfront_eyebrows_02',
      name: 'Brow Style #02',
      description: 'Defined medium arch brow',
      thumb: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_02/mindfront_eyebrows_02.png',
      obj: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_02/mind_eyebrows_02.obj',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'eyebrows',
      id: 'mindfront_eyebrows_03',
      name: 'Brow Style #03',
      description: 'Dense straight brow ridge contour',
      thumb: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_03/mindfront_eyebrows_03.png',
      obj: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_03/mind_eyebrows_03.obj',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'eyebrows',
      id: 'mindfront_eyebrows_04',
      name: 'Brow Style #04',
      description: 'Subtle tapered brow mesh',
      thumb: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_04/mindfront_eyebrows_04.png',
      obj: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_04/mind_eyebrows_04.obj',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'eyebrows',
      id: 'mindfront_eyebrows_05',
      name: 'Brow Style #05',
      description: 'High arched outer peak',
      thumb: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_05/mindfront_eyebrows_05.png',
      obj: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_05/mind_eyebrows_05.obj',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'eyebrows',
      id: 'mindfront_eyebrows_06',
      name: 'Brow Style #06',
      description: 'Bushy forensic male brow contour',
      thumb: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_06/mindfront_eyebrows_06.png',
      obj: 'models/eyebrows01_cc0/eyebrows/mindfront_eyebrows_06/mind_eyebrows_06.obj',
      license: 'CC0 - mindfront',
    ),
  ];

  // 4. EYELASHES (Real MakeHuman OBJ Meshes)
  static const List<ForensicAsset> eyelashAssets = [
    ForensicAsset(
      slot: 'eyelashes',
      id: 'mindfront_eyelashes_01',
      name: 'Lashes Style #01',
      description: 'Natural upper and lower eyelid fringe',
      thumb: 'models/eyelashes01_cc0/eyelashes/mindfront_eyelashes_01/mindfront_eyelashes_01.png',
      obj: 'models/eyelashes01_cc0/eyelashes/mindfront_eyelashes_01/mind_eyelashes_01.obj',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'eyelashes',
      id: 'mindfront_eyelashes_02',
      name: 'Lashes Style #02',
      description: 'Dense curved lash mesh',
      thumb: 'models/eyelashes01_cc0/eyelashes/mindfront_eyelashes_02/mindfront_eyelashes_02.png',
      obj: 'models/eyelashes01_cc0/eyelashes/mindfront_eyelashes_02/mind_eyelashes_02.obj',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'eyelashes',
      id: 'mindfront_eyelashes_03',
      name: 'Lashes Style #03',
      description: 'Long prominent lash fringe',
      thumb: 'models/eyelashes01_cc0/eyelashes/mindfront_eyelashes_03/mindfront_eyelashes_03.png',
      obj: 'models/eyelashes01_cc0/eyelashes/mindfront_eyelashes_03/mind_eyelashes_03.obj',
      license: 'CC0 - mindfront',
    ),
  ];

  // 5. HAIR (Real MakeHuman 3D Meshes & Textures)
  static const List<ForensicAsset> hairAssets = [
    ForensicAsset(
      slot: 'hair',
      id: 'short01',
      name: 'Classic Short Crop',
      description: 'Neat cranial parted hair strands',
      thumb: 'models/hair/short01/short01.png',
      obj: 'models/hair/short01/short01.obj',
      texture: 'models/hair/short01/short01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hair',
      id: 'short02',
      name: 'Side Part Executive',
      description: 'Formal side-parted hairstyle',
      thumb: 'models/hair/short02/short02.png',
      obj: 'models/hair/short02/short02.obj',
      texture: 'models/hair/short02/short02_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hair',
      id: 'bob01',
      name: 'Layered Bob Cut',
      description: 'Medium layered hair framing jawline',
      thumb: 'models/hair/bob01/bob01.png',
      obj: 'models/hair/bob01/bob01.obj',
      texture: 'models/hair/bob01/bob01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hair',
      id: 'afro01',
      name: 'Volumetric Afro',
      description: 'Full textured afro crown',
      thumb: 'models/hair/afro01/afro01.png',
      obj: 'models/hair/afro01/afro01.obj',
      texture: 'models/hair/afro01/afro_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hair',
      id: 'braid01',
      name: 'Braided Style',
      description: 'Intricate woven braid contour',
      thumb: 'models/hair/braid01/braid01.png',
      obj: 'models/hair/braid01/braid01.obj',
      texture: 'models/hair/braid01/braid01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hair',
      id: 'ponytail01',
      name: 'High Ponytail',
      description: 'Swept back tied ponytail',
      thumb: 'models/hair/ponytail01/ponytail01.png',
      obj: 'models/hair/ponytail01/ponytail01.obj',
      texture: 'models/hair/ponytail01/ponytail01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hair',
      id: 'long01',
      name: 'Long Flowing Waves',
      description: 'Shoulder-length waving hair strands',
      thumb: 'models/hair/long01/long01.png',
      obj: 'models/hair/long01/long01.obj',
      texture: 'models/hair/long01/long01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hair',
      id: 'short03',
      name: 'Textured Crew Cut',
      description: 'Tapered short crew crop',
      thumb: 'models/hair/short03/short03.png',
      obj: 'models/hair/short03/short03.obj',
      texture: 'models/hair/short03/short03_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
  ];

  // 6. GLASSES
  static const List<ForensicAsset> glassesAssets = [
    ForensicAsset(
      slot: 'glasses',
      id: 'classic',
      name: 'Rectangular Frame',
      description: 'Forensic metal-acetate spectacles with lenses',
      license: 'Built-in',
    ),
    ForensicAsset(
      slot: 'glasses',
      id: 'round',
      name: 'Round Wireframe',
      description: 'Circular wireframe glasses over nose bridge',
      license: 'Built-in',
    ),
  ];

  // 7. NOSE (Real MakeHuman Morph Deformation Targets)
  static const List<ForensicAsset> noseAssets = [
    ForensicAsset(
      slot: 'nose',
      id: 'elvs_bulbous_nose_1',
      name: 'Bulbous Nose',
      description: 'Rounded nasal tip anatomical vertex morph',
      thumb: 'models/nose01_cc0 (2)/targets/nose/elvs_bulbous_nose_1.png',
      target: 'models/nose01_cc0 (2)/targets/nose/elvs_bulbous_nose_1.target',
      license: 'CC0 - elvs',
    ),
    ForensicAsset(
      slot: 'nose',
      id: 'elvs_nose_widening_1',
      name: 'Wide Nose Bridge',
      description: 'Expanded nasal alar and bridge width morph',
      thumb: 'models/nose01_cc0 (2)/targets/nose/elvs_nose_widening_1.png',
      target: 'models/nose01_cc0 (2)/targets/nose/elvs_nose_widening_1.target',
      license: 'CC0 - elvs',
    ),
    ForensicAsset(
      slot: 'nose',
      id: 'habanero_nostril_flare',
      name: 'Flared Nostrils',
      description: 'Lateral nostril wings flare morph',
      thumb: 'models/nose01_cc0 (2)/targets/nose/habanero_nostril_flare.png',
      target: 'models/nose01_cc0 (2)/targets/nose/habanero_nostril_flare.target',
      license: 'CC0 - habanero',
    ),
    ForensicAsset(
      slot: 'nose',
      id: 'jujube_greek_nose',
      name: 'Greek Nose',
      description: 'Straight dorsal bridge from forehead to tip',
      thumb: 'models/nose01_cc0 (2)/targets/nose/jujube_greek_nose.png',
      target: 'models/nose01_cc0 (2)/targets/nose/jujube_greek_nose.target',
      license: 'CC0 - jujube',
    ),
  ];

  // 8. EARS (Real MakeHuman Morph Deformation Targets)
  static const List<ForensicAsset> earAssets = [
    ForensicAsset(
      slot: 'ears',
      id: 'elvs_flap_ears_1',
      name: 'Prominent Ears',
      description: 'Lateral outward ear projection morph',
      thumb: 'models/ears01_cc0/targets/ears/elvs_flap_ears_1.png',
      target: 'models/ears01_cc0/targets/ears/elvs_flap_ears_1.target',
      license: 'CC0 - elvs',
    ),
    ForensicAsset(
      slot: 'ears',
      id: 'elvs_ear_flap_bottom_out',
      name: 'Everted Lobe',
      description: 'Outward angled lower ear lobe morph',
      thumb: 'models/ears01_cc0/targets/ears/elvs_ear_flap_bottom_out.png',
      target: 'models/ears01_cc0/targets/ears/elvs_ear_flap_bottom_out.target',
      license: 'CC0 - elvs',
    ),
    ForensicAsset(
      slot: 'ears',
      id: 'mindfront_ear_detail',
      name: 'Anatomical Concha',
      description: 'Defined antihelix and conchal bowl morph',
      thumb: 'models/ears01_cc0/targets/ears/mindfront_ear_detail.png',
      target: 'models/ears01_cc0/targets/ears/mindfront_ear_detail.target',
      license: 'CC0 - mindfront',
    ),
  ];

  // 9. SKIN MATERIALS (Real MakeHuman Diffuse Textures)
  static const List<ForensicAsset> skinAssets = [
    ForensicAsset(
      slot: 'skin',
      id: 'jartur69_middleage_slavic_male',
      name: 'Slavic Middle-Aged Male',
      description: 'MakeHuman diffuse skin with facial beard and body features',
      thumb: 'models/MALE SKIN\'/skins/jartur69_middleage_slavic_male_with_genitals_and_beard/jartur69_middleage_slavic_male_with_genitals_and_beard.png',
      texture: 'models/MALE SKIN\'/skins/jartur69_middleage_slavic_male_with_genitals_and_beard/Jartur_mid_old_Slavic_Male_with_Genitals_and_Beard_lsdif_lighter.png',
      license: 'CC0 - Jartur69',
    ),
    ForensicAsset(
      slot: 'skin',
      id: 'rehmanpolanski_skin_viking_tattoos',
      name: 'Viking Tattoo Skin',
      description: 'Diffuse texture with warrior runic chest and facial tattoos',
      thumb: 'models/MALE SKIN\'/skins/rehmanpolanski_skin_viking_tattoos/rehmanpolanski_skin_viking_tattoos.png',
      texture: 'models/MALE SKIN\'/skins/rehmanpolanski_skin_viking_tattoos/viking_male_diffuse.png',
      license: 'CC0 - Rehman Polanski',
    ),
    ForensicAsset(
      slot: 'skin',
      id: 'mindfront_aksel_skin',
      name: 'Aksel Male Skin',
      description: 'High-res realistic male epidermal diffuse texture',
      thumb: 'models/MALE SKIN\'/skins/mindfront_aksel_skin/Aksel_Skin_diffuse.png',
      texture: 'models/MALE SKIN\'/skins/mindfront_aksel_skin/Aksel_Skin_diffuse.png',
      license: 'CC0 - mindfront',
    ),
    ForensicAsset(
      slot: 'skin',
      id: 'middleage_eurasian_female',
      name: 'Eurasian Female Skin',
      description: 'Detailed female facial and body epidermal texture',
      thumb: 'models/FEMALE SKIN/skins/onlytheghosts_middle_aged_eurasian_female/middleage_eurasian_female_diffuse.png',
      texture: 'models/FEMALE SKIN/skins/onlytheghosts_middle_aged_eurasian_female/middleage_eurasian_female_diffuse.png',
      license: 'CC0 - onlytheghosts',
    ),
    ForensicAsset(
      slot: 'skin',
      id: 'creamy_female',
      name: 'Porcelain Female Skin',
      description: 'Smooth Scandinavian female complexion',
      thumb: 'models/FEMALE SKIN/skins/skalldyrssuppe_creamy_female/creamy_female_diffuse.png',
      texture: 'models/FEMALE SKIN/skins/skalldyrssuppe_creamy_female/creamy_female_diffuse.png',
      license: 'CC0 - skalldyrssuppe',
    ),
    ForensicAsset(
      slot: 'skin',
      id: 'fair',
      name: 'Fair Studio Tone',
      description: 'Natural fair baseline studio tone',
      license: 'Studio PBR',
    ),
    ForensicAsset(
      slot: 'skin',
      id: 'tan',
      name: 'Tan Bronze Tone',
      description: 'Warm sun-kissed bronze tone',
      license: 'Studio PBR',
    ),
    ForensicAsset(
      slot: 'skin',
      id: 'dark',
      name: 'Deep Melanin Tone',
      description: 'Rich dark complexion tone',
      license: 'Studio PBR',
    ),
  ];

  // 10. EYES (Real MakeHuman Eye Textures)
  static const List<ForensicAsset> eyeAssets = [
    ForensicAsset(
      slot: 'eyes',
      id: 'bobby_03_diffuse_amber_eyes',
      name: 'Amber Eyes',
      description: 'Warm gold-amber iris texture',
      thumb: 'models/system_eye_materials01_cc0/eyes/materials/bobby_03_diffuse_amber_eyes/bobby_03_diffuse_amber_eyes.png',
      texture: 'models/system_eye_materials01_cc0/eyes/materials/bobby_03_diffuse_amber_eyes/makehuman_eye_diffuse_amber.png',
      license: 'CC0 - bobby',
    ),
    ForensicAsset(
      slot: 'eyes',
      id: 'bobby_03_diffuse_blue_eyes',
      name: 'Blue Eyes',
      description: 'Deep oceanic blue iris texture',
      thumb: 'models/system_eye_materials01_cc0/eyes/materials/bobby_03_diffuse_blue_eyes/bobby_03_diffuse_blue_eyes.png',
      texture: 'models/system_eye_materials01_cc0/eyes/materials/bobby_03_diffuse_blue_eyes/makehuman_eye_diffuse_blue.png',
      license: 'CC0 - bobby',
    ),
    ForensicAsset(
      slot: 'eyes',
      id: 'mindfront_brown_eye_02',
      name: 'Brown Eyes',
      description: 'Rich dark hazel-brown iris texture',
      thumb: 'models/system_eye_materials01_cc0/eyes/materials/mindfront_brown_eye_02/mindfront_brown_eye_02.png',
      texture: 'models/system_eye_materials01_cc0/eyes/materials/mindfront_brown_eye_02/brown_eye_02.png',
      license: 'CC0 - mindfront',
    ),
  ];

  // 11. HATS / HEADWEAR (Real MakeHuman Fedora 3D Meshes)
  static const List<ForensicAsset> hatAssets = [
    ForensicAsset(
      slot: 'hats',
      id: 'fedora01',
      name: 'Detective Fedora',
      description: 'Classic felt brimmed investigator fedora hat',
      thumb: 'models/clothes/fedora01/fedora01.png',
      obj: 'models/clothes/fedora01/fedora.obj',
      texture: 'models/clothes/fedora01/fedora_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'hats',
      id: 'fedora_cocked',
      name: 'Angled Fedora',
      description: 'Cocked tilted brim fedora',
      thumb: 'models/clothes/fedora_cocked/fedora_cocked.png',
      obj: 'models/clothes/fedora_cocked/fedora_cocked.obj',
      texture: 'models/clothes/fedora_cocked/fedora_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
  ];

  // 12. OUTFITS / CLOTHING (Real MakeHuman Suits & Workwear)
  static const List<ForensicAsset> outfitAssets = [
    ForensicAsset(
      slot: 'outfits',
      id: 'male_elegantsuit01',
      name: 'Formal Detective Suit',
      description: 'Two-piece tailored formal suit and dress shirt',
      thumb: 'models/clothes/male_elegantsuit01/male_elegantsuit01.png',
      obj: 'models/clothes/male_elegantsuit01/male_elegantsuit01.obj',
      texture: 'models/clothes/male_elegantsuit01/male_elegantsuit01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'outfits',
      id: 'male_casualsuit01',
      name: 'Casual Streetwear Suit',
      description: 'Modern casual jacket and pants',
      thumb: 'models/clothes/male_casualsuit01/male_casualsuit01.png',
      obj: 'models/clothes/male_casualsuit01/male_casualsuit01.obj',
      texture: 'models/clothes/male_casualsuit01/male_casualsuit01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
    ForensicAsset(
      slot: 'outfits',
      id: 'male_worksuit01',
      name: 'Industrial Worksuit',
      description: 'Heavy-duty utilitarian work uniform',
      thumb: 'models/clothes/male_worksuit01/male_worksuit01.png',
      obj: 'models/clothes/male_worksuit01/male_worksuit01.obj',
      texture: 'models/clothes/male_worksuit01/male_worksuit01_diffuse.png',
      license: 'CC0 - MakeHuman',
    ),
  ];
}
