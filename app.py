from flask import Flask, jsonify, request, send_from_directory, render_template_string
import json
import os

app = Flask(__name__)

MEDIA_FOLDER = 'media'
PLAYLIST_FILE = 'playlists.json'
DEVICES_FILE = 'devices.json'

os.makedirs(MEDIA_FOLDER, exist_ok=True)

for f in [PLAYLIST_FILE, DEVICES_FILE]:
    if not os.path.exists(f):
        with open(f, 'w') as file:
            json.dump({}, file)

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Billboard Admin</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }
        h1 { color: #333; }
        section { background: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 8px; }
        input, select, button { padding: 8px 12px; margin: 5px; border-radius: 4px; border: 1px solid #ccc; }
        button { background: #4CAF50; color: white; border: none; cursor: pointer; }
        button:hover { background: #45a049; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #eee; }
        .delete { background: #e74c3c; }
    </style>
</head>
<body>
    <h1>🎬 Billboard Admin Dashboard</h1>

    <section>
        <h2>Register Device</h2>
        <input id="deviceId" placeholder="Device ID (e.g. device_001)" />
        <input id="deviceName" placeholder="Business name" />
        <input id="deviceCategory" placeholder="Category (e.g. barber)" />
        <button onclick="registerDevice()">Register</button>
    </section>

    <section>
        <h2>Upload Media</h2>
        <input type="file" id="mediaFile" accept="image/*,video/*" />
        <input id="mediaCategory" placeholder="Ad category (e.g. barber)" />
        <input id="mediaDuration" placeholder="Duration (seconds)" type="number" value="10" />
        <button onclick="uploadMedia()">Upload</button>
    </section>

    <section>
        <h2>Media Library</h2>
        <div id="mediaList">Loading...</div>
    </section>

    <section>
        <h2>Devices</h2>
        <div id="deviceList">Loading...</div>
    </section>

    <script>
        async function registerDevice() {
            const id = document.getElementById('deviceId').value;
            const name = document.getElementById('deviceName').value;
            const category = document.getElementById('deviceCategory').value;
            await fetch('/device/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, name, category})
            });
            alert('Device registered!');
            loadDevices();
        }

        async function uploadMedia() {
            const file = document.getElementById('mediaFile').files[0];
            const category = document.getElementById('mediaCategory').value;
            const duration = document.getElementById('mediaDuration').value;
            const form = new FormData();
            form.append('file', file);
            form.append('category', category);
            form.append('duration', duration);
            await fetch('/media/upload', {method: 'POST', body: form});
            alert('Uploaded!');
            loadMedia();
        }

        async function loadMedia() {
            const r = await fetch('/media/list');
            const data = await r.json();
            const div = document.getElementById('mediaList');
            if (data.length === 0) { div.innerHTML = 'No media uploaded yet.'; return; }
            div.innerHTML = '<table><tr><th>Filename</th><th>Category</th><th>Duration</th></tr>' +
                data.map(m => `<tr><td>${m.filename}</td><td>${m.category}</td><td>${m.duration}s</td></tr>`).join('') +
                '</table>';
        }

        async function loadDevices() {
            const r = await fetch('/devices');
            const data = await r.json();
            const div = document.getElementById('deviceList');
            const keys = Object.keys(data);
            if (keys.length === 0) { div.innerHTML = 'No devices registered yet.'; return; }
            div.innerHTML = '<table><tr><th>ID</th><th>Name</th><th>Category</th></tr>' +
                keys.map(k => `<tr><td>${k}</td><td>${data[k].name}</td><td>${data[k].category}</td></tr>`).join('') +
                '</table>';
        }

        loadMedia();
        loadDevices();
    </script>
</body>
</html>
'''

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/status')
def status():
    return jsonify({"status": "Billboard server running"})

@app.route('/device/register', methods=['POST'])
def register_device():
    data = request.json
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    devices[data['id']] = {'name': data['name'], 'category': data['category']}
    with open(DEVICES_FILE, 'w') as f:
        json.dump(devices, f)
    return jsonify({"status": "registered"})

@app.route('/devices')
def get_devices():
    with open(DEVICES_FILE, 'r') as f:
        return jsonify(json.load(f))

@app.route('/media/upload', methods=['POST'])
def upload_media():
    file = request.files['file']
    category = request.form.get('category', 'general')
    duration = request.form.get('duration', 10)
    filename = file.filename
    file.save(os.path.join(MEDIA_FOLDER, filename))
    with open(PLAYLIST_FILE, 'r') as f:
        playlists = json.load(f)
    if 'library' not in playlists:
        playlists['library'] = []
    playlists['library'].append({'filename': filename, 'category': category, 'duration': int(duration)})
    with open(PLAYLIST_FILE, 'w') as f:
        json.dump(playlists, f)
    return jsonify({"status": "uploaded"})

@app.route('/media/list')
def list_media():
    with open(PLAYLIST_FILE, 'r') as f:
        playlists = json.load(f)
    return jsonify(playlists.get('library', []))

@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

@app.route('/playlist/<device_id>')
def get_playlist(device_id):
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    with open(PLAYLIST_FILE, 'r') as f:
        playlists = json.load(f)
    device = devices.get(device_id, {})
    device_category = device.get('category', '')
    library = playlists.get('library', [])
    filtered = [item for item in library if item.get('category') != device_category]
    return jsonify(filtered)

if __name__ == '__main__':
    app.run(debug=True)

