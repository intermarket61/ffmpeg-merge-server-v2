from flask import Flask, request, send_file, after_this_request, jsonify
import subprocess
import os
import uuid
import requests

app = Flask(__name__)
TMP_DIR = "/tmp"
def cleanup_files(*paths):
    @after_this_request
    def _cleanup(response):
        for p in paths:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        return response
# --- Security: protect endpoints with a shared secret ---
MERGE_SECRET = os.environ.get("MERGE_SECRET", "")

def require_secret():
    """
    Require header x-merge-secret to match MERGE_SECRET (set in Render env vars).
    If MERGE_SECRET is empty, we treat it as misconfigured and deny access.
    """
    if not MERGE_SECRET:
        return jsonify({"error": "Server not configured: MERGE_SECRET missing"}), 500

    provided = request.headers.get("x-merge-secret", "")
    if provided != MERGE_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    return None

def save_file(file, suffix):
    filename = f"{uuid.uuid4().hex}_{suffix}"
    path = os.path.join(TMP_DIR, filename)
    file.save(path)
    return path

def download_to_tmp(url, suffix, timeout=60):
    """
    Download a remote URL (e.g., Pexels/S3 presigned URL) to /tmp and return path.
    """
    filename = f"{uuid.uuid4().hex}_{suffix}"
    path = os.path.join(TMP_DIR, filename)

    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return path

@app.route("/", methods=["GET"])
def health_check():
    return "FFmpeg Merge Server is running."

@app.route("/merge", methods=["POST"])
def merge_video_audio():
    # Require secret for this endpoint
    auth_err = require_secret()
    if auth_err:
        return auth_err

    # ---- MODE A: Upload files (current behavior) ----
    if "video" in request.files and "audio" in request.files:
        video_path = save_file(request.files["video"], "video.mp4")
        audio_path = save_file(request.files["audio"], "audio.mp3")
cleanup_files(video_path, audio_path, output_path)
    # ---- MODE B: Provide URLs (cleaner behavior) ----
    else:
        data = request.get_json(silent=True) or {}
        video_url = data.get("video_url")
        audio_url = data.get("audio_url")

        if not video_url or not audio_url:
            return jsonify({"error": "Missing video/audio. Provide files (video,audio) or JSON (video_url,audio_url)."}), 400

        try:
            video_path = download_to_tmp(video_url, "video.mp4")
            audio_path = download_to_tmp(audio_url, "audio.mp3")
        except requests.RequestException as e:
            return jsonify({"error": "Failed to download input URLs", "details": str(e)}), 400

    output_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}_merged.mp4")

    command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        return send_file(output_path, mimetype="video/mp4", as_attachment=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg failed", "details": str(e)}), 500

@app.route("/image-audio", methods=["POST"])
def merge_image_audio():
    auth_err = require_secret()
    if auth_err:
        return auth_err

    if "image" not in request.files or "audio" not in request.files:
        return jsonify({"error": "Missing image or audio file"}), 400

    image_path = save_file(request.files["image"], "image.png")
    audio_path = save_file(request.files["audio"], "audio.mp3")
    output_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}_imageaudio.mp4")
cleanup_files(image_path, audio_path, output_path)
    command = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        "-pix_fmt", "yuv420p",
        "-tune", "stillimage",
        "-vf", "scale=1280:720",
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        return send_file(output_path, mimetype="video/mp4", as_attachment=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg failed", "details": str(e)}), 500

@app.route("/caption-merge", methods=["POST"])
def merge_with_captions():
    auth_err = require_secret()
    if auth_err:
        return auth_err

    if "video" not in request.files or "subtitle" not in request.files:
        return jsonify({"error": "Missing video or subtitle file"}), 400

    video_path = save_file(request.files["video"], "video.mp4")
    subtitle_path = save_file(request.files["subtitle"], "captions.srt")
    output_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}_captioned.mp4")
cleanup_files(video_path, subtitle_path, output_path)
    command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={subtitle_path}",
        "-c:a", "copy",
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        return send_file(output_path, mimetype="video/mp4", as_attachment=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "FFmpeg failed", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
