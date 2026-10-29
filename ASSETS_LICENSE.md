# 3D Asset Licenses & Attributions

This document records the licensing, sources, and attribution information for 3D assets and anatomical attachment configurations used in the **Neural Crime** forensic composite generator.

---

### Core Anatomy & System Assets
* **Base Human Meshes**: `male.glb`, `female.glb`, `head.glb` (derived from MakeHuman / MB-Lab topology)
  * **License**: CC0 1.0 Universal (Public Domain Dedication)
  * **Source**: [MakeHuman Community](https://www.makehumancommunity.org)
  * **Attribution**: MakeHuman Team & Community Contributors

---

### Procedural & Modeled Forensic Asset Catalog
* **Hairstyles (`short_crop`, `side_part`, `curly`, `bob`)**:
  * **License**: CC0 1.0 Universal
  * **Description**: Anatomical cranial hair mesh models calibrated to the MakeHuman vertex coordinate system.
* **Facial Hair (`full`, `goatee`, `stubble`, `mustache`)**:
  * **License**: CC0 1.0 Universal
  * **Description**: Precision mandibular and lip contour geometries anchored to nasal and chin landmark indices.
* **Eyewear & Spectacles (`classic`, `round`)**:
  * **License**: CC-BY 4.0 / CC0
  * **Description**: Forensic rectangular acetate and round wireframe spectacles.
* **Skin Complexions (`fair`, `olive`, `tan`, `dark`, `clay`)**:
  * **License**: CC0 1.0 Universal
  * **Description**: PBR materials calibrated for natural melanin representation.

---

### Model-Specific Landmark Calibrations
* `male.glb` Crown: $Y=1.780\text{ m}$, Eye Level: $Y=1.662\text{ m}$, Nose Tip: $Y=1.626\text{ m}$, Chin: $Y=1.485\text{ m}$.
* `female.glb` Crown: $Y=1.680\text{ m}$, Eye Level: $Y=1.571\text{ m}$, Nose Tip: $Y=1.536\text{ m}$, Chin: $Y=1.405\text{ m}$.

