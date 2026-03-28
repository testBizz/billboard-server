from flask import Flask, jsonify, request, send_from_directory, render_template_string
from datetime import datetime, timezone
import cloudinary
import cloudinary.uploader
import os
from supabase import create_client

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
CLOUDINARY_CLOUD = os.environ.get("CLOUDINARY_CLOUD")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

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
        button:hover { opacity: 0.9; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #eee; }
        .online { color: green; font-weight: bold; }
        .offline { color: red; font-weight: bold; }
        .btn-delete { background: #e74c3c; }
    </style>
</head>
<body>
    <h1>Billboard Admin Dashboard</h1>

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
        <button onclick="loadMedia()">Refresh</button>
        <div id="mediaList">Loading...</div>
    </section>

    <section>
        <h2>Devices</h2>
        <button onclick="loadDevices()">Refresh</button>
        <div id="deviceList">Loading...</div>
    </section>

    <section>
        <h2>Preview Device Playlist</h2>
        <input id="previewDeviceId" placeholder="Device ID (e.g. device_001)" />
        <button onclick="previewPlaylist()">Preview</button>
        <div id="previewArea"></div>
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
            if (data.length === 0) {
                div.innerHTML = 'No media uploaded yet.';
                return;
            }
            div.innerHTML = '<table><tr><th>Filename</th><th>Category</th><th>Duration</th><th>Preview</th><th>Action</th></tr>' +
                data.map(m => '<tr><td>' + m.filename + '</td><td>' + m.category + '</td><td>' + m.duration + 's</td><td><a href="' + m.url + '" target="_blank">View</a></td><td><button class="btn-delete" onclick="deleteMedia(' + m.id + ')">Delete</button></td></tr>').join('') +
                '</table>';
        }

        async function deleteMedia(id) {
            if (!confirm('Are you sure you want to delete this media?')) return;
            await fetch('/media/delete/' + id, {method: 'DELETE'});
            loadMedia();
        }

        async function loadDevices() {
            const r = await fetch('/devices');
            const data = await r.json();
            const div = document.getElementById('deviceList');
            if (data.length === 0) {
                div.innerHTML = 'No devices registered yet.';
                return;
            }
            div.innerHTML = '<table><tr><th>ID</th><th>Name</th><th>Category</th><th>Status</th><th>Last Seen</th><th>Action</th></tr>' +
                data.map(function(d) {
                    var status = d.online ? '<span class="online">Online</span>' : '<span class="offline">Offline</span>';
                    var lastSeen = d.last_seen ? new Date(d.last_seen).toLocaleString() : 'Never';
                    return '<tr><td>' + d.id + '</td><td>' + d.name + '</td><td>' + d.category + '</td><td>' + status + '</td><td>' + lastSeen + '</td><td><button class="btn-delete" onclick="deleteDevice(\'' + d.id + '\')">Delete</button></td></tr>';
                }).join('') +
                '</table>';
        }

        async function deleteDevice(id) {
            if (!confirm('Are you sure you want to delete this device?')) return;
            await fetch('/device/delete/' + id, {method: 'DELETE'});
            loadDevices();
        }

        async function previewPlaylist() {
            const deviceId = document.getElementById('previewDeviceId').value;
            const r = await fetch('/playlist/' + deviceId);
            const playlist = await r.json();
            const div = document.getElementById('previewArea');
            if (playlist.length === 0) {
                div.innerHTML = 'No media for this device.';
                return;
            }
            let index = 0;
            div.innerHTML = '<div style="margin-top:10px;"><img id="previewImg" src="' + playlist[0].url + '" style="max-width:100%;max-height:400px;border-radius:8px;" /><p id="previewLabel" style="text-align:center;">' + playlist[0].filename + ' - ' + playlist[0].duration + 's</p></div>';
            setInterval(function() {
                index = (index + 1) % playlist.length;
                document.getElementById('previewImg').src = playlist[index].url;
                document.getElementById('previewLabel').innerText = playlist[index].filename + ' - ' + playlist[index].duration + 's';
            }, playlist[0].duration * 1000);
        }

        loadMedia();
        loadDevices();
        setInterval(loadDevices, 30000);
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
    supabase.table('devices').upsert({
        'id': data['id'],
        'name': data['name'],
        'category': data['category']
    }).execute()
    return jsonify({"status": "registered"})

@app.route('/devices')
def get_devices():
    devices = supabase.table('devices').select('*').execute().data
    heartbeats = supabase.table('heartbeats').select('*').execute().data
    hb_map = {h['device_id']: h['last_seen'] for h in heartbeats}
    now = datetime.now(timezone.utc)
    for device in devices:
        last = hb_map.get(device['id'])
        if last:
            last_seen = datetime.fromisoformat(last)
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            diff = (now - last_seen).total_seconds()
            device['online'] = diff < 600
            device['last_seen'] = last
        else:
            device['online'] = False
            device['last_seen'] = None
    return jsonify(devices)

@app.route('/device/delete/<device_id>', methods=['DELETE'])
def delete_device(device_id):
    supabase.table('devices').delete().eq('id', device_id).execute()
    supabase.table('heartbeats').delete().eq('device_id', device_id).execute()
    return jsonify({"status": "deleted"})

@app.route('/heartbeat/<device_id>', methods=['POST'])
def heartbeat(device_id):
    now = datetime.now(timezone.utc).isoformat()
    supabase.table('heartbeats').upsert({
        'device_id': device_id,
        'last_seen': now
    }).execute()
    return jsonify({"status": "ok"})

@app.route('/media/upload', methods=['POST'])
def upload_media():
    file = request.files['file']
    category = request.form.get('category', 'general')
    duration = request.form.get('duration', 10)
    result = cloudinary.uploader.upload(file, resource_type='auto')
    url = result['secure_url']
    filename = file.filename
    supabase.table('media_library').insert({
        'filename': filename,
        'category': category,
        'duration': int(duration),
        'url': url
    }).execute()
    return jsonify({"status": "uploaded"})

@app.route('/media/list')
def list_media():
    media = supabase.table('media_library').select('*').execute().data
    return jsonify(media)

@app.route('/media/delete/<int:media_id>', methods=['DELETE'])
def delete_media(media_id):
    media = supabase.table('media_library').select('*').eq('id', media_id).execute().data
    if media:
        public_id = media[0]['url'].split('/')[-1].split('.')[0]
        cloudinary.uploader.destroy(public_id)
    supabase.table('media_library').delete().eq('id', media_id).execute()
    return jsonify({"status": "deleted"})

@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory('media', filename)

@app.route('/playlist/<device_id>')
def get_playlist(device_id):
    devices = supabase.table('devices').select('*').eq('id', device_id).execute().data
    device_category = devices[0]['category'] if devices else ''
    media = supabase.table('media_library').select('*').execute().data
    filtered = [m for m in media if m.get('category') != device_category]
    return jsonify(filtered)

if __name__ == '__main__':
    app.run(debug=True)
