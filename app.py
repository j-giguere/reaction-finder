import json
from pathlib import Path

from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Load image catalog at startup
DATA_DIR = Path(__file__).parent / "data"
with open(DATA_DIR / "images.json") as f:
    IMAGE_CATALOG = json.load(f)

# Build lookup dict by id for quick access
IMAGES_BY_ID = {img["id"]: img for img in IMAGE_CATALOG["images"]}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/react", methods=["POST"])
def react():
    data = request.get_json()
    prompt = data.get("prompt", "")

    # For now, always return the test image
    # Future: Use Ollama LLM to select appropriate reaction image
    image = IMAGES_BY_ID["dr-manhattan-understands"]

    return jsonify({
        "image_url": f"/static/images/{image['filename']}",
        "description": image["description"],
        "tags": image["tags"],
        "prompt": prompt
    })


if __name__ == "__main__":
    app.run(debug=True)
