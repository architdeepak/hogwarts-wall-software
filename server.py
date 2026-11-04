from flask import Flask, send_from_directory, request, jsonify
import json
import os
import sys

app = Flask(__name__)

# Parse profile argument (kd or sq)
PROFILE = "kd"  # default
if len(sys.argv) > 1 and sys.argv[1].lower() in ("kd", "sq"):
    PROFILE = sys.argv[1].lower()

CONFIG_FILE = f"config_{PROFILE}.json"
VIDEOS_DIR = f"videos_{PROFILE}"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/videos/<path:filename>")
def serve_video(filename):
    return send_from_directory(VIDEOS_DIR, filename)

@app.route("/config", methods=["GET"])
def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return jsonify(json.load(f))
    return jsonify({"frames": [], "resolution": {"width": 3840, "height": 2160}})

@app.route("/config", methods=["POST"])
def save_config():
    data = request.json
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "saved"})

@app.route("/list-videos")
def list_videos():
    if not os.path.exists(VIDEOS_DIR):
        os.makedirs(VIDEOS_DIR)
        return jsonify([])
    videos = [f for f in os.listdir(VIDEOS_DIR) if f.endswith((".mp4", ".webm", ".mov", ".avi", ".mkv"))]
    return jsonify(videos)

if __name__ == "__main__":
    if not os.path.exists(VIDEOS_DIR):
        os.makedirs(VIDEOS_DIR)
    print("=" * 50)
    print(f"Photo Wall Video Server [{PROFILE.upper()}]")
    print("=" * 50)
    print(f"Profile: {PROFILE} | Videos: {VIDEOS_DIR} | Config: {CONFIG_FILE}")
    print("Open http://localhost:5000 in your browser")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
