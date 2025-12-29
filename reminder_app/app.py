from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
from data_manager import DataManager

app = Flask(__name__)
data_manager = DataManager()

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

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
