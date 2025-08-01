from flask import Flask, request, send_file
import subprocess
import os
import uuid

app = Flask(__name__)

@app.route('/merge', methods=['POST'])
def merge_video_audio():
    if 'video' not in request.files or 'audio' not in request.files:
        return {'error': 'Missing video or audio file'}, 400

    video_file = request.files['video']
    audio_file = request.files['audio']

    video_filename = f"{uuid.uuid4().hex}_video.mp4"
    audio_filename = f"{uuid.uuid4().hex}_audio.mp3"
    output_filename = f"{uuid.uuid4().hex}_merged.mp4"

    video_path = os.path.join("/tmp", video_filename)
    audio_path = os.path.join("/tmp", audio_filename)
    output_path = os.path.join("/tmp", output_filename)

    video_file.save(video_path)
    audio_file.save(audio_path)

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
    except subprocess.CalledProcessError as e:
        return {'error': 'FFmpeg failed', 'details': str(e)}, 500

    return send_file(output_path, mimetype='video/mp4', as_attachment=True, download_name=output_filename)

@app.route('/', methods=['GET'])
def health_check():
    return "FFmpeg Merge Server is running."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
