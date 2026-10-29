class CompositeParams {
  String model;
  double scaleX;
  double scaleY;
  double scaleZ;
  String gender;
  String focus; // 'face' or 'body'
  String beard; // 'none', 'full', 'goatee', 'stubble', 'mustache'
  String hair; // 'none', 'short', 'curly', 'side_part'
  String glasses; // 'none', 'classic', 'round'
  bool isConfirmed;
  String activeFeature;

  // Papillon-style Forensic Anatomical Controls
  double jawWidth;
  double chinLength;
  double noseWidth;
  double noseLength;
  double eyeSpacing;
  double eyeSize;
  double lipThickness;
  double mouthWidth;
  double cheekbones;

  CompositeParams({
    this.model = 'male.glb',
    this.scaleX = 1.0,
    this.scaleY = 1.0,
    this.scaleZ = 1.0,
    this.gender = 'male',
    this.focus = 'face',
    this.beard = 'none',
    this.hair = 'none',
    this.glasses = 'none',
    this.isConfirmed = false,
    this.activeFeature = 'Face & Jaw',
    this.jawWidth = 1.0,
    this.chinLength = 1.0,
    this.noseWidth = 1.0,
    this.noseLength = 1.0,
    this.eyeSpacing = 1.0,
    this.eyeSize = 1.0,
    this.lipThickness = 1.0,
    this.mouthWidth = 1.0,
    this.cheekbones = 1.0,
  });

  CompositeParams copyWith({
    String? model,
    double? scaleX,
    double? scaleY,
    double? scaleZ,
    String? gender,
    String? focus,
    String? beard,
    String? hair,
    String? glasses,
    bool? isConfirmed,
    String? activeFeature,
    double? jawWidth,
    double? chinLength,
    double? noseWidth,
    double? noseLength,
    double? eyeSpacing,
    double? eyeSize,
    double? lipThickness,
    double? mouthWidth,
    double? cheekbones,
  }) {
    return CompositeParams(
      model: model ?? this.model,
      scaleX: scaleX ?? this.scaleX,
      scaleY: scaleY ?? this.scaleY,
      scaleZ: scaleZ ?? this.scaleZ,
      gender: gender ?? this.gender,
      focus: focus ?? this.focus,
      beard: beard ?? this.beard,
      hair: hair ?? this.hair,
      glasses: glasses ?? this.glasses,
      isConfirmed: isConfirmed ?? this.isConfirmed,
      activeFeature: activeFeature ?? this.activeFeature,
      jawWidth: jawWidth ?? this.jawWidth,
      chinLength: chinLength ?? this.chinLength,
      noseWidth: noseWidth ?? this.noseWidth,
      noseLength: noseLength ?? this.noseLength,
      eyeSpacing: eyeSpacing ?? this.eyeSpacing,
      eyeSize: eyeSize ?? this.eyeSize,
      lipThickness: lipThickness ?? this.lipThickness,
      mouthWidth: mouthWidth ?? this.mouthWidth,
      cheekbones: cheekbones ?? this.cheekbones,
    );
  }

  Map<String, dynamic> toAnatomyMap() => {
        'jawWidth': jawWidth,
        'chinLength': chinLength,
        'noseWidth': noseWidth,
        'noseLength': noseLength,
        'eyeSpacing': eyeSpacing,
        'eyeSize': eyeSize,
        'lipThickness': lipThickness,
        'mouthWidth': mouthWidth,
        'cheekbones': cheekbones,
      };

  Map<String, dynamic> toJson() => {
        'model': model,
        'scale_x': scaleX,
        'scale_y': scaleY,
        'scale_z': scaleZ,
        'gender': gender,
        'focus': focus,
        'beard': beard,
        'hair': hair,
        'glasses': glasses,
        'is_confirmed': isConfirmed,
        'active_feature': activeFeature,
        'anatomy': toAnatomyMap(),
      };
}

class ApiService {
  static const String baseUrl = 'http://127.0.0.1:8000';

  static Future<Map<String, dynamic>> parseDescription({
    required String caseId,
    required String text,
    required CompositeParams current,
  }) async {
    return _localFallbackParse(text: text, caseId: caseId, current: current);
  }

  static Future<bool> confirmComposite({
    required String caseId,
    required CompositeParams params,
  }) async {
    return true;
  }

  static Map<String, dynamic> _localFallbackParse({
    required String text,
    required String caseId,
    required CompositeParams current,
  }) {
    final lower = text.toLowerCase().trim();
    String model = current.model;
    String gender = current.gender;
    double sx = current.scaleX;
    double sy = current.scaleY;
    double sz = current.scaleZ;
    String focus = current.focus;
    String beard = current.beard;
    String hair = current.hair;
    String glasses = current.glasses;

    double jawW = current.jawWidth;
    double chinL = current.chinLength;
    double noseW = current.noseWidth;
    double noseL = current.noseLength;
    double eyeSp = current.eyeSpacing;
    double eyeSz = current.eyeSize;
    double lipTh = current.lipThickness;
    double mouthW = current.mouthWidth;
    double cheeks = current.cheekbones;

    bool isFeatureConfirmed = false;
    List<String> notes = [];

    // Confirmations
    if (lower == 'okay' ||
        lower == 'ok' ||
        lower.contains('looks good') ||
        lower.contains('looks okay') ||
        lower.contains('was okay') ||
        lower.contains('confirm') ||
        lower.contains('accurate') ||
        lower.contains('perfect')) {
      isFeatureConfirmed = true;
    }

    // 1. NOSE SCULPTING
    if (lower.contains('wider nose') || lower.contains('broad nose') || lower.contains('wide nose')) {
      noseW = 1.25;
      notes.add('Widened nose bridge and nostrils (1.25x)');
    } else if (lower.contains('narrow nose') || lower.contains('thin nose') || lower.contains('slim nose')) {
      noseW = 0.85;
      notes.add('Narrowed nose bridge (0.85x)');
    }
    if (lower.contains('longer nose') || lower.contains('long nose') || lower.contains('big nose')) {
      noseL = 1.18;
      notes.add('Extended nose length (1.18x)');
    } else if (lower.contains('short nose') || lower.contains('small nose')) {
      noseL = 0.88;
      notes.add('Shortened nose length (0.88x)');
    }

    // 2. EYE SCULPTING
    if (lower.contains('bigger eyes') || lower.contains('big eyes') || lower.contains('large eyes')) {
      eyeSz = 1.20;
      notes.add('Enlarged eye sockets (1.20x)');
    } else if (lower.contains('smaller eyes') || lower.contains('small eyes')) {
      eyeSz = 0.88;
      notes.add('Reduced eye size (0.88x)');
    }
    if (lower.contains('eyes further apart') || lower.contains('wide set eyes')) {
      eyeSp = 1.18;
      notes.add('Increased eye spacing (1.18x)');
    } else if (lower.contains('eyes closer') || lower.contains('close set eyes')) {
      eyeSp = 0.88;
      notes.add('Decreased eye spacing (0.88x)');
    }

    // 3. MOUTH & LIPS SCULPTING
    if (lower.contains('thicker lips') || lower.contains('full lips') || lower.contains('pouty lips') || lower.contains('big lips')) {
      lipTh = 1.30;
      notes.add('Increased lip fullness (1.30x)');
    } else if (lower.contains('thin lips') || lower.contains('smaller lips')) {
      lipTh = 0.80;
      notes.add('Reduced lip thickness (0.80x)');
    }
    if (lower.contains('wider mouth') || lower.contains('wide mouth') || lower.contains('wide smile')) {
      mouthW = 1.18;
      notes.add('Expanded mouth width (1.18x)');
    }

    // 4. JAW & CHIN SCULPTING
    if (lower.contains('wider jaw') || lower.contains('square jaw') || lower.contains('broad jaw') || lower.contains('angular jaw')) {
      jawW = 1.22;
      notes.add('Broadened jawline / square jaw structure (1.22x)');
    } else if (lower.contains('narrow jaw') || lower.contains('pointed chin') || lower.contains('slim jaw')) {
      jawW = 0.86;
      chinL = 1.12;
      notes.add('Narrowed jaw to tapered / pointed chin');
    }
    if (lower.contains('high cheekbones') || lower.contains('prominent cheekbones')) {
      cheeks = 1.20;
      notes.add('Raised cheekbone prominence (1.20x)');
    }

    // 5. BEARD & FACIAL HAIR
    if (lower.contains('clean shaven') || lower.contains('no beard') || lower.contains('shaved')) {
      beard = 'none';
      notes.add('Clean shaven');
    } else if (lower.contains('goatee')) {
      beard = 'goatee';
      notes.add('Added Goatee beard');
    } else if (lower.contains('stubble') || lower.contains('shadow')) {
      beard = 'stubble';
      notes.add('Added Stubble shadow');
    } else if (lower.contains('mustache') || lower.contains('moustache')) {
      beard = 'mustache';
      notes.add('Added Mustache');
    } else if (lower.contains('beard') || lower.contains('full beard')) {
      beard = 'full';
      notes.add('Added Full Beard');
    }

    // 6. HAIR & GLASSES
    if (lower.contains('bald') || lower.contains('no hair')) {
      hair = 'none';
      notes.add('Set to Bald');
    } else if (lower.contains('curly') || lower.contains('afro')) {
      hair = 'curly';
      notes.add('Added Curly hair');
    } else if (lower.contains('side part') || lower.contains('parted')) {
      hair = 'side_part';
      notes.add('Added Side-parted hair');
    } else if (lower.contains('short hair') || lower.contains('crop')) {
      hair = 'short';
      notes.add('Added Short hair');
    }

    if (lower.contains('no glasses')) {
      glasses = 'none';
      notes.add('Removed glasses');
    } else if (lower.contains('round glasses')) {
      glasses = 'round';
      notes.add('Added Round wireframe glasses');
    } else if (lower.contains('glasses') || lower.contains('spectacles')) {
      glasses = 'classic';
      notes.add('Added Rectangular glasses');
    }

    String reply;
    if (isFeatureConfirmed) {
      reply =
          '✓ Feature confirmed and locked into the forensic composite! Moving to next characteristic: What about their nose, lips, or distinctive markings?';
    } else if (notes.isNotEmpty) {
      reply =
          'Updated 3D facial vertices: ${notes.join("; ")}. Notice the anatomical change on the 3D model! You can adjust with more details or say "okay" to confirm.';
    } else {
      reply =
          'Recorded. You can adjust any facial feature (e.g. "wider nose", "thicker lips", "bigger eyes", "square jaw", "beard", "glasses") or say "okay" to confirm.';
    }

    return {
      'status': 'success',
      'case_id': caseId,
      'gender': gender,
      'model': model,
      'scale_x': sx,
      'scale_y': sy,
      'scale_z': sz,
      'focus': focus,
      'beard': beard,
      'hair': hair,
      'glasses': glasses,
      'is_feature_confirmed': isFeatureConfirmed,
      'investigator_reply': reply,
      'actions': notes,
      'anatomy': {
        'jawWidth': jawW,
        'chinLength': chinL,
        'noseWidth': noseW,
        'noseLength': noseL,
        'eyeSpacing': eyeSp,
        'eyeSize': eyeSz,
        'lipThickness': lipTh,
        'mouthWidth': mouthW,
        'cheekbones': cheeks,
      }
    };
  }
}
