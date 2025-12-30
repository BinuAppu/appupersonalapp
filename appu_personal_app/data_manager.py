import json
import os
import uuid
import base64
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data.json")
KB_FILE = os.path.join(BASE_DIR, "knowledgebase.json")
SECURE_FILE = os.path.join(BASE_DIR, "secure.json")

#DATA_FILE = "data.json"

class DataManager:
    def __init__(self, data_file=DATA_FILE):
        self.data_file = data_file
        self.load_data()

    def load_data(self):
        if not os.path.exists(self.data_file):
            self.data = {"reminders": [], "tasks": []}
            self.save_data()
        else:
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = {"reminders": [], "tasks": []}

    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=4)

    # --- Reminders ---
    def add_reminder(self, title, description, date_str, recurrence):
        reminder = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "date": date_str,
            "recurrence": recurrence,
            "created_at": datetime.now().isoformat(),
            "comments": []
        }
        self.data["reminders"].append(reminder)
        self.save_data()
        return reminder

    def get_upcoming_reminders(self, weeks=1):
        """
        Get reminders occurring within the next 'weeks' weeks.
        Handles recurrence by dynamically projecting dates.
        """
        upcoming = []
        today = datetime.now().date()
        end_date = today + timedelta(weeks=weeks)
        
        for reminder in self.data["reminders"]:
            try:
                rem_date = datetime.strptime(reminder["date"], "%Y-%m-%d").date()
            except ValueError:
                continue

            # If it's a past one-time reminder, skip (unless we want to show missed ones, but 'upcoming' usually implies future)
            # However, for recurring, we need to find the next occurrence relative to today.
            
            next_occurrence = self._get_next_occurrence(rem_date, reminder["recurrence"], today)
            
            if next_occurrence and today <= next_occurrence <= end_date:
                # Return a copy with the calculated display date
                rem_copy = reminder.copy()
                rem_copy["display_date"] = next_occurrence.strftime("%Y-%m-%d")
                upcoming.append(rem_copy)

        # Sort by display_date
        upcoming.sort(key=lambda x: x["display_date"])
        return upcoming
    
    def _get_next_occurrence(self, start_date, recurrence, relative_to):
        """
        Calculate the next occurrence of a reminder after or on 'relative_to' date.
        """
        if recurrence == "None":
            return start_date if start_date >= relative_to else None
        
        current_occurrence = start_date
        
        while current_occurrence < relative_to:
            if recurrence == "Daily":
                current_occurrence += timedelta(days=1)
            elif recurrence == "Weekly":
                current_occurrence += timedelta(weeks=1)
            elif recurrence == "Monthly":
                year = current_occurrence.year
                month = current_occurrence.month
                day = current_occurrence.day
                month += 1
                if month > 12:
                    month = 1
                    year += 1
                import calendar
                _, last_day = calendar.monthrange(year, month)
                new_day = min(day, last_day)
                current_occurrence = current_occurrence.replace(year=year, month=month, day=new_day)
            elif recurrence == "Yearly":
                try:
                    current_occurrence = current_occurrence.replace(year=current_occurrence.year + 1)
                except ValueError:
                    current_occurrence = current_occurrence.replace(year=current_occurrence.year + 1, day=28)
        
        return current_occurrence

    def get_projected_reminders(self, start_date_obj, end_date_obj):
        """
        Project all occurrences of all reminders between start_date_obj and end_date_obj.
        """
        projected = []
        for reminder in self.data["reminders"]:
            try:
                base_date = datetime.strptime(reminder["date"], "%Y-%m-%d").date()
            except ValueError:
                continue

            recurrence = reminder["recurrence"]
            
            if recurrence == "None":
                if start_date_obj <= base_date <= end_date_obj:
                    rem_copy = reminder.copy()
                    rem_copy["display_date"] = base_date.strftime("%Y-%m-%d")
                    projected.append(rem_copy)
                continue

            # For recurring reminders, find all occurrences in range
            current = base_date
            
            # Catch up to or start from the earliest needed date
            if current < start_date_obj:
                current = self._get_next_occurrence(base_date, recurrence, start_date_obj)
            
            # Collect all until end_date
            while current <= end_date_obj:
                rem_copy = reminder.copy()
                rem_copy["display_date"] = current.strftime("%Y-%m-%d")
                projected.append(rem_copy)
                
                # Advance to next occurrence
                if recurrence == "Daily":
                    current += timedelta(days=1)
                elif recurrence == "Weekly":
                    current += timedelta(weeks=1)
                elif recurrence == "Monthly":
                    year = current.year
                    month = current.month
                    day = base_date.day # Always try to use the original day
                    month += 1
                    if month > 12:
                        month = 1
                        year += 1
                    import calendar
                    _, last_day = calendar.monthrange(year, month)
                    new_day = min(day, last_day)
                    current = current.replace(year=year, month=month, day=new_day)
                elif recurrence == "Yearly":
                    try:
                        current = current.replace(year=current.year + 1)
                    except ValueError:
                        current = current.replace(year=current.year + 1, day=28)
                else:
                    break # Should not happen for proyected cases we handle
        
        return projected

    def get_all_reminders(self):
        return self.data["reminders"]
        
    def delete_reminder(self, reminder_id):
        self.data["reminders"] = [r for r in self.data["reminders"] if r["id"] != reminder_id]
        self.save_data()

    def update_reminder(self, reminder_id, title, description, date_str, recurrence):
        for reminder in self.data["reminders"]:
            if reminder["id"] == reminder_id:
                reminder["title"] = title
                reminder["description"] = description
                reminder["date"] = date_str
                reminder["recurrence"] = recurrence
                # We don't necessarily update created_at
                self.save_data()
                return reminder
        return None

    # --- Tasks ---
    def add_task(self, title, description, status="Yet to Start"):
        task = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "comments": []
        }
        self.data["tasks"].append(task)
        self.save_data()
        return task

    def get_active_tasks(self):
        return [t for t in self.data["tasks"] if t["status"] != "Completed"]
    
    def get_all_tasks(self):
        return self.data["tasks"]

    def update_task_status(self, task_id, new_status):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                task["status"] = new_status
                self.save_data()
                return True
        return False

    def update_task(self, task_id, title, description, status):
        for task in self.data["tasks"]:
            if task["id"] == task_id:
                task["title"] = title
                task["description"] = description
                task["status"] = status
                self.save_data()
                return task
        return None
        
    def delete_task(self, task_id):
        self.data["tasks"] = [t for t in self.data["tasks"] if t["id"] != task_id]
        self.save_data()

    # --- Comments ---
    def add_comment(self, item_type, item_id, text):
        if item_type == 'task':
            items = self.data["tasks"]
        elif item_type == 'reminder':
            items = self.data["reminders"]
        else:
            return None

        for item in items:
            if item["id"] == item_id:
                comment = {
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                }
                item.setdefault("comments", []).append(comment)
                self.save_data()
                return comment
        return None

    def get_latest_comments(self, limit=5):
        all_comments = []
        for r in self.data["reminders"]:
            for c in r.get("comments", []):
                all_comments.append({
                    "text": c["text"],
                    "timestamp": c["timestamp"],
                    "item_title": r["title"],
                    "item_type": "Reminder"
                })
        for t in self.data["tasks"]:
            for c in t.get("comments", []):
                all_comments.append({
                    "text": c["text"],
                    "timestamp": c["timestamp"],
                    "item_title": t["title"],
                    "item_type": "Task"
                })
        
        all_comments.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_comments[:limit]

    # --- Knowledge Base ---
    def load_kb(self):
        if not os.path.exists(KB_FILE):
            return []
        try:
            with open(KB_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def save_kb(self, kb_data):
        with open(KB_FILE, 'w') as f:
            json.dump(kb_data, f, indent=4)

    def get_kb_items(self):
        return self.load_kb()

    def add_kb_item(self, title, data, url):
        kb_data = self.load_kb()
        item = {
            "id": str(uuid.uuid4()),
            "title": title,
            "data": data,
            "url": url,
            "created_at": datetime.now().isoformat()
        }
        kb_data.append(item)
        self.save_kb(kb_data)
        return item

    def update_kb_item(self, kb_id, title, data, url):
        kb_data = self.load_kb()
        for item in kb_data:
            if item["id"] == kb_id:
                item["title"] = title
                item["data"] = data
                item["url"] = url
                self.save_kb(kb_data)
                return item
        return None

    def delete_kb_item(self, kb_id):
        kb_data = self.load_kb()
        kb_data = [item for item in kb_data if item["id"] != kb_id]
        self.save_kb(kb_data)
        return True

    def search_kb_items(self, query):
        kb_data = self.load_kb()
        if not query:
            return kb_data

        query = query.lower()
        results = []
        for item in kb_data:
            title_score = item["title"].lower().count(query)
            data_score = item["data"].lower().count(query)
            total_score = (title_score * 2) + data_score
            
            if total_score > 0:
                results.append((item, total_score))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results]

    # --- Secure Vault ---
    
    def _get_fernet(self, master_key, salt):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)

    def load_secure_data(self):
        if not os.path.exists(SECURE_FILE):
            return None
        with open(SECURE_FILE, 'r') as f:
            return json.load(f)

    def save_secure_data(self, data):
        with open(SECURE_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def init_secure_vault(self, master_key):
        """Initializes the secure vault with a master key."""
        if os.path.exists(SECURE_FILE):
            return False # Already exists
        
        salt = os.urandom(16)
        salt_b64 = base64.b64encode(salt).decode('utf-8')
        
        f = self._get_fernet(master_key, salt)
        # Encrypt a validation token to verify the key later
        validation_token = f.encrypt(b"VALID").decode('utf-8')
        
        data = {
            "salt": salt_b64,
            "validation": validation_token,
            "items": []
        }
        self.save_secure_data(data)
        return True

    def validate_master_key(self, master_key):
        """Returns the Fernet object if key is valid, else None."""
        data = self.load_secure_data()
        if not data:
            return None
        
        try:
            salt = base64.b64decode(data['salt'])
            f = self._get_fernet(master_key, salt)
            decrypted = f.decrypt(data['validation'].encode())
            if decrypted == b"VALID":
                return f
        except Exception:
            pass
        return None

    def get_secure_items(self, master_key):
        f = self.validate_master_key(master_key)
        if not f:
            raise ValueError("Invalid Master Key")
        
        data = self.load_secure_data()
        decrypted_items = []
        for item in data['items']:
            try:
                decrypted_items.append({
                    "id": item["id"],
                    "title": f.decrypt(item["title"].encode()).decode(),
                    "user_id": f.decrypt(item["user_id"].encode()).decode(),
                    "password": f.decrypt(item["password"].encode()).decode(),
                    "url": f.decrypt(item["url"].encode()).decode(),
                    "notes": f.decrypt(item["notes"].encode()).decode(),
                })
            except Exception:
                pass # Skip items that fail to decrypt (shouldn't happen if key is valid)
        return decrypted_items

    def add_secure_item(self, master_key, item_data):
        f = self.validate_master_key(master_key)
        if not f:
            raise ValueError("Invalid Master Key")
        
        data = self.load_secure_data()
        
        new_item = {
            "id": str(uuid.uuid4()),
            "title": f.encrypt(item_data['title'].encode()).decode(),
            "user_id": f.encrypt(item_data.get('user_id', '').encode()).decode(),
            "password": f.encrypt(item_data['password'].encode()).decode(),
            "url": f.encrypt(item_data.get('url', '').encode()).decode(),
            "notes": f.encrypt(item_data.get('notes', '').encode()).decode(),
        }
        
        data['items'].append(new_item)
        self.save_secure_data(data)
        
        # Return decrypted version for UI
        item_data['id'] = new_item['id']
        return item_data

    def update_secure_item(self, master_key, item_id, item_data):
        f = self.validate_master_key(master_key)
        if not f:
            raise ValueError("Invalid Master Key")
        
        data = self.load_secure_data()
        for item in data['items']:
            if item['id'] == item_id:
                item["title"] = f.encrypt(item_data['title'].encode()).decode()
                item["user_id"] = f.encrypt(item_data.get('user_id', '').encode()).decode()
                item["password"] = f.encrypt(item_data['password'].encode()).decode()
                item["url"] = f.encrypt(item_data.get('url', '').encode()).decode()
                item["notes"] = f.encrypt(item_data.get('notes', '').encode()).decode()
                self.save_secure_data(data)
                item_data['id'] = item_id
                return item_data
        return None

    def delete_secure_item(self, master_key, item_id):
        f = self.validate_master_key(master_key)
        if not f:
            raise ValueError("Invalid Master Key")
        
        data = self.load_secure_data()
        data['items'] = [i for i in data['items'] if i['id'] != item_id]
        self.save_secure_data(data)
        return True
