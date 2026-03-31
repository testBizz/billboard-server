from flask import Flask, jsonify, request, send_from_directory, render_template
from datetime import datetime, timezone
import cloudinary
import cloudinary.uploader
import os
from supabase import create_client
from sendgrid import SendGridAPIClient
from sendgrid.mail import Mail
import threading

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



@app.route('/')
def dashboard():
    return render_template('dashboard.html')

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
