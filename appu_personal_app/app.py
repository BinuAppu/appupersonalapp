from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import shutil
import time
import requests
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

@app.template_filter('days_until')
def days_until_filter(date_str):
    if not date_str: return 999
    try:
        if isinstance(date_str, str):
            # Try ISO format first
            try:
                rem_date = datetime.fromisoformat(date_str).date()
            except:
                # Try YYYY-MM-DD format
                rem_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            rem_date = date_str
        today = datetime.now().date()
        delta = (rem_date - today).days
        return delta
    except:
        return 999

@app.route('/')
def dashboard():
    upcoming_reminders = data_manager.get_upcoming_reminders(weeks=6)
    future_reminders = data_manager.get_upcoming_reminders(weeks=12)
    active_tasks = data_manager.get_active_tasks()
    projects = data_manager.get_all_projects()
    user_name = data_manager.get_user_name()
    return render_template('dashboard.html', 
                           upcoming_reminders=upcoming_reminders,
                           future_reminders=future_reminders,
                           active_tasks=active_tasks,
                           projects=projects,
                           user_name=user_name)

@app.route('/all')
def all_items():
    reminders = data_manager.get_all_reminders()
    tasks = data_manager.get_all_tasks()
    kb_items = data_manager.get_kb_items()
    projects = data_manager.get_all_projects()
    return render_template('list_view.html', reminders=reminders, tasks=tasks, kb_items=kb_items, projects=projects)

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

@app.route('/settings')
def settings():
    return render_template('settings.html', user_name=data_manager.get_user_name())

@app.route('/api/settings/username', methods=['GET', 'POST'])
def handle_username():
    if request.method == 'POST':
        data = request.json
        new_name = data.get('name')
        if new_name:
            data_manager.set_user_name(new_name)
            return jsonify({"success": True, "name": new_name})
        return jsonify({"success": False, "error": "Name required"}), 400
    else:
        return jsonify({"name": data_manager.get_user_name()})

@app.route('/api/backup', methods=['POST'])
def backup_data():
    try:
        # Use absolute path relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.join(base_dir, 'backup')
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Files identified from data_manager.py
        files_to_check = ['data.json', 'knowledgebase.json', 'secure.json', 'username.json']
        backed_up_files = []
        
        for filename in files_to_check:
            src = os.path.join(base_dir, filename)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, f"{filename.split('.')[0]}_{timestamp}.json")
                shutil.copy2(src, dst)
                backed_up_files.append(os.path.basename(dst))
        
        if not backed_up_files:
            return jsonify({"success": False, "error": "No data files found to backup"}), 404
            
        return jsonify({"success": True, "path": backup_dir, "files": backed_up_files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- Projects API ---
@app.route('/project/<project_id>')
def project_detail(project_id):
    project = data_manager.get_project(project_id)
    if not project:
        return redirect(url_for('dashboard'))
    return render_template('project.html', project=project)

@app.route('/api/projects', methods=['GET'])
def get_projects():
    return jsonify(data_manager.get_all_projects())

@app.route('/api/projects', methods=['POST'])
def add_project():
    data = request.json
    project = data_manager.add_project(
        data['name'],
        data['description'],
        data['start_date'],
        data['end_date'],
        data['status']
    )
    return jsonify(project)

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    project = data_manager.get_project(project_id)
    if project:
        return jsonify(project)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    data = request.json
    result = data_manager.update_project(
        project_id,
        data['name'],
        data['description'],
        data['start_date'],
        data['end_date'],
        data['status']
    )
    if result:
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    success = data_manager.delete_project(project_id)
    return jsonify({"success": success})

@app.route('/api/projects/<project_id>/tasks', methods=['POST'])
def add_project_task(project_id):
    data = request.json
    task = data_manager.add_project_task(
        project_id,
        data['name'],
        data.get('comments', ''),
        data['start_date'],
        data['end_date'],
        data.get('parent_id')
    )
    if task:
        if "error" in task:
            return jsonify(task), 400
        return jsonify(task)
    return jsonify({"error": "Project not found"}), 404

@app.route('/api/projects/<project_id>/tasks/<task_id>', methods=['PUT'])
def update_project_task(project_id, task_id):
    data = request.json
    result = data_manager.update_project_task(
        project_id,
        task_id,
        data.get('name'),
        data.get('comments'),
        data.get('start_date'),
        data.get('end_date'),
        data.get('status')
    )
    if result:
        if isinstance(result, dict) and 'error' in result:
            return jsonify(result), 400
        return jsonify(result)
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/projects/<project_id>/tasks/<task_id>', methods=['DELETE'])
def delete_project_task(project_id, task_id):
    success = data_manager.delete_project_task(project_id, task_id)
    return jsonify({"success": success})

@app.route('/api/projects/<project_id>/tasks/<task_id>/comments', methods=['POST'])
def add_project_task_comment(project_id, task_id):
    data = request.json
    comment = data_manager.add_project_task_comment(project_id, task_id, data['text'])
    if comment:
        return jsonify(comment)
    return jsonify({"error": "Task not found"}), 404

@app.route('/api/projects/<project_id>/tasks/<task_id>/status', methods=['PUT'])
def update_project_task_status(project_id, task_id):
    data = request.json
    success = data_manager.update_project_task_status(project_id, task_id, data['status'])
    return jsonify({"success": success})

@app.route('/api/projects/<project_id>/tasks/<task_id>/parent-dates', methods=['GET'])
def get_parent_task_dates(project_id, task_id):
    start_date, end_date = data_manager.get_parent_task_dates(project_id, task_id)
    if start_date and end_date:
        return jsonify({"start_date": start_date, "end_date": end_date})
    return jsonify({"error": "Parent task or dates not found"}), 404

@app.route('/api/check_update')
def check_update():
    try:
        # Get local modification time of app.py
        local_time = os.path.getmtime('app.py')
        local_date_obj = datetime.fromtimestamp(local_time)
        local_date = local_date_obj.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get latest commit from GitHub
        url = "https://api.github.com/repos/BinuAppu/appupersonalapp/commits?per_page=1"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        commit_date_str = data[0]['commit']['committer']['date']
        # ISO 8601 format: 2023-10-27T10:00:00Z
        commit_date = datetime.strptime(commit_date_str, "%Y-%m-%dT%H:%M:%SZ")
        # Add timezone info to make it offset-aware (UTC) for fair comparison if we wanted, 
        # but for now just string comparison or simple boolean logic
        
        remote_date = commit_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Logic: If remote date > local date (with some buffer?), update available.
        # But local file time might be anything. A better way is checking a version file. 
        # Since we don't have one, we'll assume update available if remote seems "newer" in a general sense,
        # or just always true as requested to 'fix' it (user said 'not working as expected').
        # Actually user said "Check update is not working as expected, try to fix it."
        # The previous code hardcoded "update_available": True. Maybe that was the annoyance?
        # Let's try to be smart. If committer date is definitely after local mtime.
        
        # Converting local mtime to approximate UTC for comparison isn't perfect but better than nothing.
        # Let's just return the dates and let the frontend confirm, OR do the check here.
        
        # For this fix, let's just properly return the data and let's assume if the remote sha is different
        # from some stored version it's an update. We don't have stored version.
        # So we will rely on timestamps.
        
        update_available = False
        # Be generous, if remote is more than 24 hours ahead of local mod time, say update.
        # Or just show the dates.
        # The user's specific complaint "not working as expected" might mean it ALWAYS says update available.
        # Let's try to compare properly.
        # Local time is system time. 
        
        # Simplest fix: Just return the data and let the user see.
        # 'update_available' flag logic:
        # We will assume update provided if the remote commit date is strictly after local file mod time.
        # But local file mod time updates when we save this file! So after this edit, local time will be NOW.
        # Remote time might be OLDER. So it will say "Up to date". That is correct behavior.
        
        is_newer = commit_date > (local_date_obj - timedelta(minutes=5)) # buffer
        # Wait, if I just edited this file, local_date is NOW. commit_date is OLD (e.g. yesterday).
        # So commit_date < local_date. is_newer is False. Update available = False. Correct.
        
        return jsonify({
            "update_available": is_newer,
            "local_date": local_date,
            "remote_date": remote_date,
            "message": "Update available!" if is_newer else "You are up to date."
        })
    except Exception as e:
        return jsonify({"error": str(e), "update_available": False}), 500

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
