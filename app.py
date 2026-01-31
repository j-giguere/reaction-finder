import json
import logging
from pathlib import Path

from flask import Flask, render_template, jsonify, request

from config import Config
from services import OllamaService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Load image catalog at startup
DATA_DIR = Path(__file__).parent / "data"
with open(DATA_DIR / "images.json") as f:
    IMAGE_CATALOG = json.load(f)

# Build lookup dict by id for quick access
IMAGES_BY_ID = {img["id"]: img for img in IMAGE_CATALOG["images"]}

# Initialize Ollama service
ollama_service = OllamaService(IMAGE_CATALOG)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/react", methods=["POST"])
def react():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    prompt = data.get("prompt", "")
    if not prompt or not prompt.strip():
        return jsonify({"error": "Prompt is required"}), 400

    # Use Ollama to select the appropriate reaction image
    image_id = ollama_service.select_image(prompt)
    image = IMAGES_BY_ID.get(image_id)

    # Fallback safety check (should not happen, but be defensive)
    if not image:
        logger.error(f"Image ID '{image_id}' not found in catalog, using fallback")
        image = IMAGES_BY_ID[Config.FALLBACK_IMAGE_ID]

    return jsonify({
        "image_id": image["id"],
        "image_url": f"/static/images/{image['filename']}",
        "description": image["description"],
        "tags": image["tags"],
        "prompt": prompt
    })


@app.route("/api/health")
def health():
    """Health check endpoint with Ollama status."""
    ollama_available = ollama_service.is_available()

    status = {
        "status": "healthy" if ollama_available else "degraded",
        "ollama": {
            "available": ollama_available,
            "model": Config.OLLAMA_MODEL,
            "host": Config.OLLAMA_HOST,
        },
        "images_loaded": len(IMAGE_CATALOG.get("images", [])),
    }

    # Return 200 even if Ollama is down (app still works with fallback)
    return jsonify(status)


if __name__ == "__main__":
    # Log startup info
    logger.info(f"Starting Reaction Finder with Ollama model: {Config.OLLAMA_MODEL}")
    if ollama_service.is_available():
        logger.info("Ollama is available and ready")
    else:
        logger.warning("Ollama is not available - will use fallback images")

    app.run(debug=True)
