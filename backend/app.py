from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import base64
import numpy as np
import cv2
import re

app = FastAPI(
    title="Neural Crime - AI Forensic Composite API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DescriptionRequest(BaseModel):
    case_id: str
    text: str
    current_model: Optional[str] = "male.glb"
    current_scale_x: Optional[float] = 1.0
    current_scale_y: Optional[float] = 1.0
    current_scale_z: Optional[float] = 1.0
    current_focus: Optional[str] = "face"
    current_beard: Optional[str] = "none"
    current_hair: Optional[str] = "none"
    current_glasses: Optional[str] = "none"
    active_stage: Optional[str] = "face"

class ConfirmRequest(BaseModel):
    case_id: str
    confirmed_params: Dict[str, Any]

class SketchRequest(BaseModel):
    case_id: str
    image_base64: str

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Neural Crime Forensic API",
        "models_available": ["male.glb", "female.glb", "head.glb"]
    }

@app.post("/api/parse_description")
def parse_description(req: DescriptionRequest):
    text = req.text.lower().strip()
    
    model = req.current_model or "male.glb"
    scale_x = req.current_scale_x or 1.0
    scale_y = req.current_scale_y or 1.0
    scale_z = req.current_scale_z or 1.0
    gender = "female" if "female" in model else "male"
    focus = req.current_focus or "face"
    beard = req.current_beard or "none"
    hair = req.current_hair or "none"
    glasses = req.current_glasses or "none"
    
    is_feature_confirmed = False
    feedback_notes = []

    # 1. Confirmations
    confirm_patterns = [
        r'\b(okay|ok|looks good|looks okay|shape of (the )?face was okay|fine|that is fine|confirmed|confirm|accurate|perfect)\b'
    ]
    for pattern in confirm_patterns:
        if re.search(pattern, text):
            is_feature_confirmed = True
            break

    # 2. BEARD & FACIAL HAIR
    if re.search(r'\b(clean shaven|no beard|no facial hair|shaved)\b', text):
        beard = "none"
        feedback_notes.append("Clean shaven (removed beard)")
    elif re.search(r'\b(goatee)\b', text):
        beard = "goatee"
        feedback_notes.append("added 3D Goatee beard")
    elif re.search(r'\b(stubble|5 o\'?clock shadow|light beard)\b', text):
        beard = "stubble"
        feedback_notes.append("added 3D Stubble shadow")
    elif re.search(r'\b(mustache|moustache)\b', text):
        beard = "mustache"
        feedback_notes.append("added 3D Mustache")
    elif re.search(r'\b(beard|full beard|heavy beard|facial hair)\b', text):
        beard = "full"
        feedback_notes.append("added 3D Full Beard & Mustache")

    # 3. HAIR STYLES
    if re.search(r'\b(bald|no hair|shaved head)\b', text):
        hair = "none"
        feedback_notes.append("Hair set to Bald / Shaved scalp")
    elif re.search(r'\b(curly|afro|wavy hair)\b', text):
        hair = "curly"
        feedback_notes.append("added 3D Curly / Textured hair")
    elif re.search(r'\b(parted|side part|formal hair)\b', text):
        hair = "side_part"
        feedback_notes.append("added 3D Side-parted hair")
    elif re.search(r'\b(short hair|hair|crop|black hair|brown hair)\b', text):
        hair = "short"
        feedback_notes.append("added 3D Short cropped hair")

    # 4. GLASSES
    if re.search(r'\b(no glasses|without glasses)\b', text):
        glasses = "none"
        feedback_notes.append("removed glasses")
    elif re.search(r'\b(round glasses)\b', text):
        glasses = "round"
        feedback_notes.append("added 3D Round wireframe glasses")
    elif re.search(r'\b(glasses|spectacles|specs)\b', text):
        glasses = "classic"
        feedback_notes.append("added 3D Forensic rectangular glasses")

    # 5. Face Size
    if re.search(r'\b(face (little |bit )?big|bigger face|large face|large head|head big)\b', text):
        scale_x = min(1.30, scale_x + 0.08)
        scale_y = min(1.25, scale_y + 0.06)
        scale_z = min(1.25, scale_z + 0.06)
        focus = "face"
        feedback_notes.append("enlarged facial/head scale (+8%)")
    elif re.search(r'\b(face (little |bit )?small|smaller face|small head|narrow face)\b', text):
        scale_x = max(0.80, scale_x - 0.08)
        scale_y = max(0.80, scale_y - 0.06)
        focus = "face"
        feedback_notes.append("reduced facial scale (-8%)")

    # 6. Face Shape
    if re.search(r'\b(oval|egg-shaped|oblong)\b', text):
        scale_x = 0.94
        scale_y = 1.08
        scale_z = 0.96
        focus = "face"
        feedback_notes.append("adjusted facial structure to Oval")
    elif re.search(r'\b(round|circular|chubby face)\b', text):
        scale_x = 1.12
        scale_y = 0.94
        scale_z = 1.08
        focus = "face"
        feedback_notes.append("adjusted facial structure to Round")
    elif re.search(r'\b(square|strong jaw|angular|broad jaw)\b', text):
        scale_x = 1.15
        scale_y = 1.02
        scale_z = 1.10
        focus = "face"
        feedback_notes.append("adjusted to Square / Strong angular jaw")

    # Response
    if is_feature_confirmed:
        reply = (
            "✓ Feature Confirmed and Locked! Current face shape and facial features are saved. "
            "Moving to next step: How would you describe their eyes or eyebrows?"
        )
    elif feedback_notes:
        action_str = "; ".join(feedback_notes)
        reply = (
            f"Understood. I have updated the 3D model: {action_str}. "
            "Notice the beard/hair rendered on the 3D face preview on the right! You can fine-tune it or say 'okay' to confirm."
        )
    else:
        reply = (
            "Recorded. You can add features ('beard', 'mustache', 'short hair', 'curly', 'glasses') "
            "or adjust shape ('face little big', 'oval') or say 'okay' when satisfied."
        )

    return {
        "status": "success",
        "case_id": req.case_id,
        "gender": gender,
        "model": model,
        "scale_x": round(scale_x, 3),
        "scale_y": round(scale_y, 3),
        "scale_z": round(scale_z, 3),
        "focus": focus,
        "beard": beard,
        "hair": hair,
        "glasses": glasses,
        "is_feature_confirmed": is_feature_confirmed,
        "investigator_reply": reply,
        "actions": feedback_notes
    }

@app.post("/api/confirm_composite")
def confirm_composite(req: ConfirmRequest):
    return {
        "status": "confirmed",
        "case_id": req.case_id,
        "params": req.confirmed_params,
        "message": f"Composite locked and verified for Case {req.case_id}."
    }

@app.post("/api/generate_sketch")
def generate_sketch(req: SketchRequest):
    try:
        data = req.image_base64
        if "base64," in data:
            data = data.split("base64,")[1]
            
        img_bytes = base64.b64decode(data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        smoothed = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        inverted = 255 - smoothed
        blurred = cv2.GaussianBlur(inverted, (21, 21), sigmaX=0, sigmaY=0)
        sketch = cv2.divide(smoothed, 255 - blurred, scale=256)
        sketch_enhanced = cv2.equalizeHist(sketch)
        final_sketch = cv2.addWeighted(sketch, 0.7, sketch_enhanced, 0.3, 0)

        _, buffer = cv2.imencode('.png', final_sketch)
        sketch_b64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "status": "success",
            "case_id": req.case_id,
            "sketch_base64": f"data:image/png;base64,{sketch_b64}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
