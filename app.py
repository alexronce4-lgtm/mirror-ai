import base64
import io
import requests as http
from flask import Flask, render_template, request, jsonify, Response
from PIL import Image
from agents import run_analyzer, run_coach
from database import init_db, log_session, get_history
from config import GOOGLE_API_KEY

app = Flask(__name__)
init_db()


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/analyze")
def analyze():
    data = request.get_json(force=True)
    img_b64 = data.get("image", "")
    if not img_b64:
        return jsonify({"error": "No image provided"}), 400

    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]

    image = Image.open(io.BytesIO(base64.b64decode(img_b64))).convert("RGB")

    history = get_history(limit=1)
    previous = history[0] if history else None

    analysis = run_analyzer(image)
    coaching = run_coach(analysis)

    log_session({
        "risk_level":        analysis.get("risk_level"),
        "risk_score":        analysis.get("risk_score"),
        "confidence":        analysis.get("confidence"),
        "key_observations":  analysis.get("key_observations", []),
        "immediate_actions": coaching.get("immediate_actions", []),
        "megan_message":     coaching.get("megan_message"),
    })

    return jsonify({
        "risk_level":           analysis.get("risk_level"),
        "risk_score":           analysis.get("risk_score"),
        "confidence":           analysis.get("confidence"),
        "fatigue_score":        analysis.get("fatigue_score"),
        "stress_score":         analysis.get("stress_score"),
        "dehydration_score":    analysis.get("dehydration_score"),
        "eye_analysis":         analysis.get("eye_analysis"),
        "skin_analysis":        analysis.get("skin_analysis"),
        "fatigue_level":        analysis.get("fatigue_level"),
        "stress_indicators":    analysis.get("stress_indicators", []),
        "key_observations":     analysis.get("key_observations", []),
        "megan_message":        analysis.get("megan_message") or coaching.get("megan_message"),
        "immediate_actions":    analysis.get("immediate_actions") or coaching.get("immediate_actions", []),
        "wellness_tip":         analysis.get("wellness_tip"),
        "optimized_risk_score": coaching.get("optimized_risk_score"),
        "optimized_risk_level": coaching.get("optimized_risk_level"),
        "scenario_improvement": coaching.get("scenario_improvement"),
        "previous_session":     previous,
    })


GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


@app.post("/speak")
def speak():
    text = (request.get_json(force=True) or {}).get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    if not GOOGLE_API_KEY:
        return jsonify({"error": "Google API key not configured"}), 503

    resp = http.post(
        GOOGLE_TTS_URL,
        params={"key": GOOGLE_API_KEY},
        json={
            "input": {"text": text},
            "voice": {"languageCode": "en-US", "name": "en-US-Journey-F"},
            "audioConfig": {"audioEncoding": "MP3"},
        },
        timeout=15,
    )

    if resp.status_code != 200:
        return jsonify({"error": f"Google TTS error {resp.status_code}: {resp.text}"}), 502

    audio_bytes = base64.b64decode(resp.json()["audioContent"])
    return Response(audio_bytes, mimetype="audio/mpeg")


if __name__ == "__main__":
    app.run(debug=False, port=5001, ssl_context=('localhost.pem', 'localhost-key.pem'))
