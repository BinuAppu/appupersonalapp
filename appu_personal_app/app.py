from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
from data_manager import DataManager

app = Flask(__name__)
data_manager = DataManager()

@app.template_filter('short_date')
def short_date_filter(value):
    if not value: return ""
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            dt = value
        return dt.strftime('%m/%d')
    except:
        return value

@app.route('/')
def dashboard():
    upcoming_reminders = data_manager.get_upcoming_reminders(weeks=6)
    future_reminders = data_manager.get_upcoming_reminders(weeks=12)
    active_tasks = data_manager.get_active_tasks()
    return render_template('dashboard.html', 
                           upcoming_reminders=upcoming_reminders,
                           future_reminders=future_reminders,
                           active_tasks=active_tasks)

@app.route('/all')
def all_items():
    reminders = data_manager.get_all_reminders()
    tasks = data_manager.get_all_tasks()
    kb_items = data_manager.get_kb_items()
    return render_template('list_view.html', reminders=reminders, tasks=tasks, kb_items=kb_items)

@app.route('/calendar')
def calendar_view():
    today = datetime.now().date()
    start_date = today.replace(month=1, day=1) - timedelta(days=365)
    end_date = today.replace(month=12, day=31) + timedelta(days=365)
    projected = data_manager.get_projected_reminders(start_date, end_date)
    return render_template('calendar.html', reminders=projected)

@app.route('/knowledge')
def knowledge_base():
    return render_template('knowledge_base.html')

@app.route('/api/all_data')
def get_all_data():
    return jsonify({
        "reminders": data_manager.get_all_reminders(),
        "tasks": data_manager.get_all_tasks()
    })

# --- API Routes ---

@app.route('/api/reminders', methods=['POST'])
def add_reminder():
    data = request.json
    reminder = data_manager.add_reminder(
        data['title'], 
        data['description'], 
        data['date'], 
        data['recurrence']
    )
    return jsonify(reminder)

@app.route('/api/reminders/<reminder_id>', methods=['PUT'])
def update_reminder(reminder_id):
    data = request.json
    reminder = data_manager.update_reminder(
        reminder_id,
        data['title'],
        data['description'],
        data['date'],
        data['recurrence']
    )
    return jsonify(reminder)

@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    task = data_manager.add_task(
        data['title'], 
        data['description'], 
        data.get('status', 'Yet to Start')
    )
    return jsonify(task)

@app.route('/api/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    task = data_manager.update_task(
        task_id,
        data['title'],
        data['description'],
        data['status']
    )
    return jsonify(task)

@app.route('/api/comments', methods=['POST'])
def add_comment():
    data = request.json
    comment = data_manager.add_comment(
        data['item_type'], 
        data['item_id'], 
        data['text']
    )
    return jsonify(comment)

@app.route('/api/tasks/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    data = request.json
    success = data_manager.update_task_status(task_id, data['status'])
    return jsonify({"success": success})

@app.route('/api/reminders/<reminder_id>', methods=['DELETE'])
def delete_reminder(reminder_id):
    data_manager.delete_reminder(reminder_id)
    return jsonify({"success": True})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    data_manager.delete_task(task_id)
    return jsonify({"success": True})

# --- Knowledge Base API ---
@app.route('/api/kb', methods=['GET'])
def get_kb_items():
    return jsonify(data_manager.get_kb_items())

@app.route('/api/kb/search', methods=['GET'])
def search_kb_items():
    query = request.args.get('q', '')
    return jsonify(data_manager.search_kb_items(query))

@app.route('/api/kb', methods=['POST'])
def add_kb_item():
    data = request.json
    item = data_manager.add_kb_item(data['title'], data['data'], data['url'])
    return jsonify(item)

@app.route('/api/kb/<kb_id>', methods=['PUT'])
def update_kb_item(kb_id):
    data = request.json
    item = data_manager.update_kb_item(kb_id, data['title'], data['data'], data['url'])
    return jsonify(item)

@app.route('/api/kb/<kb_id>', methods=['DELETE'])
def delete_kb_item(kb_id):
    success = data_manager.delete_kb_item(kb_id)
    return jsonify({"success": success})

# --- Secure Vault API ---

@app.route('/secure')
def secure_view():
    vault_initialized = data_manager.is_secure_vault_initialized()
    return render_template('secure.html', vault_initialized=vault_initialized)

@app.route('/api/secure/init', methods=['POST'])
def init_secure_vault():
    data = request.json
    master_key = data.get('master_key')
    if not master_key:
        return jsonify({"success": False, "error": "Master Key required"}), 400
    
    success = data_manager.init_secure_vault(master_key)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Vault already exists"}), 400

@app.route('/api/secure/validate', methods=['POST'])
def validate_master_key():
    data = request.json
    master_key = data.get('master_key')
    f = data_manager.validate_master_key(master_key)
    return jsonify({"valid": f is not None})

@app.route('/api/secure/items', methods=['POST'])
def get_secure_items():
    data = request.json
    master_key = data.get('master_key')
    try:
        items = data_manager.get_secure_items(master_key)
        return jsonify(items)
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

@app.route('/api/secure/add', methods=['POST'])
def add_secure_item():
    data = request.json
    master_key = data.get('master_key')
    item_data = data.get('item')
    try:
        item = data_manager.add_secure_item(master_key, item_data)
        return jsonify(item)
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

@app.route('/api/secure/<item_id>', methods=['PUT'])
def update_secure_item(item_id):
    data = request.json
    master_key = data.get('master_key')
    item_data = data.get('item')
    try:
        item = data_manager.update_secure_item(master_key, item_id, item_data)
        return jsonify(item)
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

@app.route('/api/secure/<item_id>', methods=['DELETE']) # Note: DELETE normally doesn't have body, but many clients support it. Safer to use POST for operations needing complex auth if headers aren't used. But we can put master_key in headers or query params? Plan said body. Flask supports body in DELETE.
def delete_secure_item(item_id):
    data = request.json
    master_key = data.get('master_key')
    try:
        success = data_manager.delete_secure_item(master_key, item_id)
        return jsonify({"success": success})
    except ValueError:
        return jsonify({"error": "Invalid Master Key"}), 401

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
