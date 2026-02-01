import json
import logging
import uuid
from pathlib import Path

from flask import Flask, render_template, jsonify, request

from config import Config
from services import OllamaService, MetadataGenerator, LocalImageStorage, JsonMetadataRepository

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

# Initialize upload services
IMAGES_DIR = Path(__file__).parent / "static" / "images"
image_storage = LocalImageStorage(IMAGES_DIR)
metadata_repo = JsonMetadataRepository(DATA_DIR / "images.json")
metadata_generator = MetadataGenerator()


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


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


def generate_image_id(description: str) -> str:
    """Generate a URL-friendly ID from description."""
    # Take first few words, lowercase, replace spaces with hyphens
    words = description.lower().split()[:5]
    base_id = "-".join(words)
    # Remove non-alphanumeric chars except hyphens
    base_id = "".join(c for c in base_id if c.isalnum() or c == "-")
    # Add short UUID suffix to ensure uniqueness
    suffix = uuid.uuid4().hex[:6]
    return f"{base_id}-{suffix}"


def reload_image_catalog():
    """Reload the image catalog from disk."""
    global IMAGE_CATALOG, IMAGES_BY_ID, ollama_service
    with open(DATA_DIR / "images.json") as f:
        IMAGE_CATALOG = json.load(f)
    IMAGES_BY_ID = {img["id"]: img for img in IMAGE_CATALOG["images"]}
    # Reinitialize ollama service with new catalog
    ollama_service = OllamaService(IMAGE_CATALOG)


@app.route("/api/upload", methods=["POST"])
def upload():
    """Handle image upload with automatic metadata generation."""
    # Check if file was provided
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": f"File type not allowed. Allowed: {', '.join(Config.ALLOWED_EXTENSIONS)}"
        }), 400

    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > Config.MAX_UPLOAD_SIZE:
        max_mb = Config.MAX_UPLOAD_SIZE / (1024 * 1024)
        return jsonify({
            "success": False,
            "error": f"File too large. Maximum size: {max_mb:.0f}MB"
        }), 400

    # Generate unique filename
    original_ext = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{original_ext}"

    try:
        # Generate metadata using vision LLM
        metadata = metadata_generator.generate_metadata(file)

        # Reset file position after metadata generation read it
        file.seek(0)

        # Save image to storage
        image_url = image_storage.save_image(file, unique_filename)

        # Generate ID from description
        image_id = generate_image_id(metadata["description"])

        # Build image data
        image_data = {
            "id": image_id,
            "filename": unique_filename,
            "description": metadata["description"],
            "tags": metadata["tags"],
        }

        # Save metadata
        metadata_repo.save_metadata(image_data)

        # Reload the catalog so new image is available for selection
        reload_image_catalog()

        return jsonify({
            "success": True,
            "image": {
                "id": image_id,
                "filename": unique_filename,
                "description": metadata["description"],
                "tags": metadata["tags"],
                "image_url": image_url,
            }
        })

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({"success": False, "error": "Upload failed"}), 500


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

    app.run(host="0.0.0.0", port=8080, debug=False)
