from flask import Flask, request, send_file
import subprocess
import os
import uuid

app = Flask(__name__)
TMP_DIR = "/tmp"

def save_file(file, suffix):
    filename = f"{uuid.uuid4().hex}_{suffix}"
    path = os.path.join(TMP_DIR, filename)
    file.save(path)
    return path

@app.route('/', methods=['GET'])
def health_check():
    return "FFmpeg Merge Server is running."

@app.route('/merge', methods=['POST'])
def merge_video_audio():
    if 'video' not in request.files or 'audio' not in request.files:
        return {'error': 'Missing video or audio file'}, 400

    video_path = save_file(request.files['video'], 'video.mp4')
    audio_path = save_file(request.files['audio'], 'audio.mp3')
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
        return send_file(output_path, mimetype='video/mp4', as_attachment=True)
    except subprocess.CalledProcessError as e:
        return {'error': 'FFmpeg failed', 'details': str(e)}, 500

@app.route('/image-audio', methods=['POST'])
def merge_image_audio():
    if 'image' not in request.files or 'audio' not in request.files:
        return {'error': 'Missing image or audio file'}, 400

    image_path = save_file(request.files['image'], 'image.png')
    audio_path = save_file(request.files['audio'], 'audio.mp3')
    output_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}_imageaudio.mp4")

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
        return send_file(output_path, mimetype='video/mp4', as_attachment=True)
    except subprocess.CalledProcessError as e:
        return {'error': 'FFmpeg failed', 'details': str(e)}, 500

@app.route('/caption-merge', methods=['POST'])
def merge_with_captions():
    if 'video' not in request.files or 'subtitle' not in request.files:
        return {'error': 'Missing video or subtitle file'}, 400

    video_path = save_file(request.files['video'], 'video.mp4')
    subtitle_path = save_file(request.files['subtitle'], 'captions.srt')
    output_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}_captioned.mp4")

    command = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"subtitles={subtitle_path}",
        "-c:a", "copy",
        output_path
    ]

    try:
        subprocess.run(command, check=True)
        return send_file(output_path, mimetype='video/mp4', as_attachment=True)
    except subprocess.CalledProcessError as e:
        return {'error': 'FFmpeg failed', 'details': str(e)}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
