from flask import Flask, jsonify, request, send_from_directory
import json
import os

app = Flask(__name__)

MEDIA_FOLDER = 'media'
PLAYLIST_FILE = 'playlists.json'

os.makedirs(MEDIA_FOLDER, exist_ok=True)

if not os.path.exists(PLAYLIST_FILE):
    with open(PLAYLIST_FILE, 'w') as f:
        json.dump({}, f)

@app.route('/')
def home():
    return jsonify({"status": "Billboard server running"})

@app.route('/playlist/<device_id>')
def get_playlist(device_id):
    with open(PLAYLIST_FILE, 'r') as f:
        playlists = json.load(f)
    playlist = playlists.get(device_id, [])
    return jsonify(playlist)

@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True)
