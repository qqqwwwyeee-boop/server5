from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import hashlib
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

DB_FILE = "database.json"

def get_device_id(request):
    """Extract unique device ID from request"""
    data = request.get_json(silent=True) or {}
    return data.get('device_id', '')

def get_file_path(request):
    """Extract file path from request"""
    data = request.get_json(silent=True) or {}
    return data.get('file_path', '')

def get_file_hash(request):
    """Extract file hash from request"""
    data = request.get_json(silent=True) or {}
    return data.get('file_hash', '')

# Initialize database
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({
            "activations": {},
            "stats": {
                "total_keys": 0,
                "active_keys": 0,
                "suspended_keys": 0,
                "inactive_keys": 0
            }
        }, f, indent=2)

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Ashraf Activation Server",
        "developer": "@AShrf_771117678",
        "server_url": "https://server5-3.onrender.com"
    })

@app.route('/check/<key>', methods=['POST'])
def check_key(key):
    """Check key status with device, path and file binding"""
    key = key.upper()
    data = request.get_json(silent=True) or {}
    
    device_id = data.get('device_id')
    file_path = data.get('file_path')
    file_hash = data.get('file_hash')
    
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    
    if key in db['activations']:
        key_data = db['activations'][key].copy()
        
        # Check registered device, path and file
        registered_device = key_data.get('registered_device')
        registered_path = key_data.get('registered_path')
        registered_hash = key_data.get('registered_hash')
        
        # If key is active but no registration data (first use)
        if key_data['status'] == 'active' and not registered_device and device_id:
            # Register all data for first time
            db['activations'][key]['registered_device'] = device_id
            db['activations'][key]['registered_path'] = file_path
            db['activations'][key]['registered_hash'] = file_hash
            db['activations'][key]['first_use'] = datetime.now().isoformat()
            with open(DB_FILE, 'w') as f:
                json.dump(db, f, indent=2)
            key_data['registered_device'] = device_id
            key_data['registered_path'] = file_path
            key_data['registered_hash'] = file_hash
        
        # Verify everything matches
        if registered_device:
            errors = []
            if registered_device != device_id:
                errors.append("Different device")
            if registered_path != file_path:
                errors.append("Different path")
            if registered_hash != file_hash:
                errors.append("Different file")
            
            if errors:
                return jsonify({
                    'found': True,
                    'status': 'blocked',
                    'message': f'Access denied: {", ".join(errors)}',
                    'expiry': key_data.get('expiry', ''),
                    'activated': key_data.get('activated', '')
                }), 403
        
        # Check if temporary suspension ended
        if key_data['status'] == 'suspended' and 'resume' in key_data:
            resume_time = datetime.fromisoformat(key_data['resume'])
            if datetime.now() > resume_time:
                key_data['status'] = 'active'
                db['activations'][key]['status'] = 'active'
                if 'resume' in db['activations'][key]:
                    del db['activations'][key]['resume']
                with open(DB_FILE, 'w') as f:
                    json.dump(db, f, indent=2)
        
        return jsonify({
            'found': True,
            'status': key_data['status'],
            'expiry': key_data.get('expiry', ''),
            'activated': key_data.get('activated', ''),
            'resume': key_data.get('resume', ''),
            'months': key_data.get('months', 0),
            'registered': bool(key_data.get('registered_device'))
        })
    
    return jsonify({'found': False})

@app.route('/activate', methods=['POST'])
def activate_key():
    """Activate a new key"""
    data = request.json
    key = data.get('key', '').upper()
    months = int(data.get('months', 1))
    
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    
    if months > 0:
        expiry = (datetime.now() + timedelta(days=months*30)).isoformat()
    else:
        expiry = "permanent"
    
    db['activations'][key] = {
        'status': 'active',
        'activated': datetime.now().isoformat(),
        'expiry': expiry,
        'months': months,
        'registered_device': None,
        'registered_path': None,
        'registered_hash': None,
        'first_use': None
    }
    
    # Update statistics
    total = len(db['activations'])
    active = sum(1 for k in db['activations'].values() if k['status'] == 'active')
    suspended = sum(1 for k in db['activations'].values() if k['status'] == 'suspended')
    inactive = total - active - suspended
    
    db['stats'] = {
        'total_keys': total,
        'active_keys': active,
        'suspended_keys': suspended,
        'inactive_keys': inactive
    }
    
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)
    
    return jsonify({'success': True, 'key': key, 'expiry': expiry})

@app.route('/deactivate', methods=['POST'])
def deactivate_key():
    """Deactivate a key"""
    data = request.json
    key = data.get('key', '').upper()
    
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    
    if key in db['activations']:
        db['activations'][key]['status'] = 'inactive'
        
        # Update statistics
        total = len(db['activations'])
        active = sum(1 for k in db['activations'].values() if k['status'] == 'active')
        suspended = sum(1 for k in db['activations'].values() if k['status'] == 'suspended')
        inactive = total - active - suspended
        
        db['stats'] = {
            'total_keys': total,
            'active_keys': active,
            'suspended_keys': suspended,
            'inactive_keys': inactive
        }
        
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/extend', methods=['POST'])
def extend_key():
    """Extend key expiry"""
    data = request.json
    key = data.get('key', '').upper()
    months = int(data.get('months', 1))
    
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    
    if key in db['activations']:
        if db['activations'][key]['expiry'] != "permanent":
            current_expiry = datetime.fromisoformat(db['activations'][key]['expiry'])
            new_expiry = current_expiry + timedelta(days=months*30)
            expiry = new_expiry.isoformat()
        else:
            expiry = "permanent"
        
        db['activations'][key].update({
            'expiry': expiry,
            'months': db['activations'][key]['months'] + months,
            'status': 'active'
        })
        
        # Update statistics
        total = len(db['activations'])
        active = sum(1 for k in db['activations'].values() if k['status'] == 'active')
        suspended = sum(1 for k in db['activations'].values() if k['status'] == 'suspended')
        inactive = total - active - suspended
        
        db['stats'] = {
            'total_keys': total,
            'active_keys': active,
            'suspended_keys': suspended,
            'inactive_keys': inactive
        }
        
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        
        return jsonify({'success': True, 'key': key, 'expiry': expiry})
    
    return jsonify({'success': False})

@app.route('/suspend', methods=['POST'])
def suspend_key():
    """Temporarily suspend a key"""
    data = request.json
    key = data.get('key', '').upper()
    hours = int(data.get('hours', 1))
    
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    
    if key in db['activations']:
        resume = (datetime.now() + timedelta(hours=hours)).isoformat()
        db['activations'][key]['status'] = 'suspended'
        db['activations'][key]['resume'] = resume
        
        # Update statistics
        total = len(db['activations'])
        active = sum(1 for k in db['activations'].values() if k['status'] == 'active')
        suspended = sum(1 for k in db['activations'].values() if k['status'] == 'suspended')
        inactive = total - active - suspended
        
        db['stats'] = {
            'total_keys': total,
            'active_keys': active,
            'suspended_keys': suspended,
            'inactive_keys': inactive
        }
        
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        
        return jsonify({'success': True, 'resume': resume})
    
    return jsonify({'success': False})

@app.route('/resume', methods=['POST'])
def resume_key():
    """Resume a suspended key"""
    data = request.json
    key = data.get('key', '').upper()
    
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    
    if key in db['activations']:
        db['activations'][key]['status'] = 'active'
        if 'resume' in db['activations'][key]:
            del db['activations'][key]['resume']
        
        # Update statistics
        total = len(db['activations'])
        active = sum(1 for k in db['activations'].values() if k['status'] == 'active')
        suspended = sum(1 for k in db['activations'].values() if k['status'] == 'suspended')
        inactive = total - active - suspended
        
        db['stats'] = {
            'total_keys': total,
            'active_keys': active,
            'suspended_keys': suspended,
            'inactive_keys': inactive
        }
        
        with open(DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)
        
        return jsonify({'success': True})
    
    return jsonify({'success': False})

@app.route('/list', methods=['GET'])
def list_keys():
    """List all keys"""
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    
    keys_list = []
    for key, data in db['activations'].items():
        keys_list.append({
            'key': key,
            'status': data['status'],
            'expiry': data.get('expiry', ''),
            'activated': data.get('activated', ''),
            'registered': bool(data.get('registered_device'))
        })
    
    return jsonify({'keys': keys_list, 'total': len(keys_list)})

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    with open(DB_FILE, 'r') as f:
        db = json.load(f)
    return jsonify(db['stats'])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server running on port {port}")
    print(f"🌐 Server URL: https://server5-3.onrender.com")
    app.run(host='0.0.0.0', port=port)