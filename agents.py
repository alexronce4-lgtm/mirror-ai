import base64
import io
import logging
import traceback
import json
import re
import anthropic
from PIL import Image
from config import ANTHROPIC_API_KEY, ANALYZER_PROMPT, COACH_PROMPT

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_MODEL = "claude-sonnet-4-5"

logging.basicConfig(
    filename="/tmp/mirror_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("mirror")

_ANALYZER_DEFAULT = {
    "risk_score": 50,
    "risk_level": "MODERATE",
    "confidence": 0.5,
    "fatigue_score": 50,
    "stress_score": 50,
    "dehydration_score": 40,
    "eye_analysis": {"redness": 30, "drooping": 40, "dark_circles": 40},
    "skin_analysis": {"pallor": 30, "hydration": 50, "tension_lines": 30},
    "fatigue_level": "MODERATE",
    "stress_indicators": ["Unable to assess — image quality may be insufficient", "Please retake in better lighting"],
    "key_observations": ["Eyes: analysis unavailable", "Skin: analysis unavailable", "Overall: please retake photo in good lighting"],
    "megan_message": "I wasn't able to fully read your photo — try again in natural light and I'll give you a proper read.",
    "immediate_actions": ["Drink a glass of water", "Take 3 slow deep breaths", "Step away from screens for 5 minutes"],
    "wellness_tip": "Good lighting and a straight-on angle help me give you the most accurate reading.",
}

_COACH_DEFAULT = {
    "immediate_actions": ["Drink a glass of water", "Take 3 deep breaths", "Step away from screens for 5 minutes"],
    "optimized_risk_score": 30,
    "optimized_risk_level": "LOW",
    "scenario_improvement": "With basic self-care steps, your wellness score can improve significantly.",
    "megan_message": "I'm here for you! Even small steps toward self-care make a big difference.",
}


def _parse_json(text: str, default: dict) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return default


def run_analyzer(image: Image.Image) -> dict:
    _log.info("run_analyzer called — image size: %s mode: %s", image.size, image.mode)
    try:
        _log.debug("Encoding image to JPEG bytes")
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        image_data = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
        _log.debug("Image encoded — %d bytes", len(buf.getvalue()))

        _log.debug("Sending request to %s", _MODEL)
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": ANALYZER_PROMPT},
                ],
            }],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        _log.debug("Response received — text length: %d", len(text))
        _log.debug("Raw response text: %s", text)

        result = _parse_json(text, _ANALYZER_DEFAULT)
        _log.info("run_analyzer succeeded — risk_level: %s score: %s", result.get("risk_level"), result.get("risk_score"))
        return result
    except Exception as e:
        _log.error("run_analyzer failed: %s", e)
        _log.error(traceback.format_exc())
        traceback.print_exc()
        print(f"[ANALYZER ERROR] {e}")
        return _ANALYZER_DEFAULT


def run_coach(analysis: dict) -> dict:
    try:
        prompt = f"{COACH_PROMPT}\n\nAnalysis data:\n{json.dumps(analysis, indent=2)}"
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return _parse_json(text, _COACH_DEFAULT)
    except Exception as e:
        print(f"[COACH ERROR] {e}")
        return _COACH_DEFAULT
