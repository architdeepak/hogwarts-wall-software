from flask import Flask, send_from_directory, request, jsonify
import argparse
import json
import os

app = Flask(__name__)

def configure(profile):
    global CONFIG_FILE, VIDEOS_DIR
    CONFIG_FILE = f"config_{profile}.json"
    VIDEOS_DIR = f"videos_{profile}"


configure("kd")

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
    parser = argparse.ArgumentParser(description="Run the portrait wall display.")
    parser.add_argument("profile", nargs="?", choices=("kd", "sq"), default="kd", type=str.lower)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    configure(args.profile)
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    app.run(host=args.host, port=5000)
