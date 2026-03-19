# Axolotl Personal Dashboard 🦎

Welcome to **Axolotl**, a modern, comprehensive personal productivity and organization dashboard built to "regenerate" your daily workflow. With an emphasis on fluid design, glassmorphism, and intuitive item management, Axolotl makes organizing your life visually stunning and effortlessly practical.

## 🌟 Key Features
- **Modern Dashboard:** A central hub showing active tasks, dynamic active projects, and upcoming reminders all running on an ultra-modern, fluid fluid layout.
- **Task Management:** Create, track, and manage granular tasks with full kanban-style board views and status updates.
- **Project Tracking:** Group activities under broader Projects with strict timelines, dynamic countdowns, and completion statuses.
- **Secure Vault:** A localized, fully-encrypted zero-knowledge vault module for storing sensitive credentials securely (all encrypted data is kept on-device).
- **Knowledge Base:** Save important notes, links, ideas, and snippets utilizing easy quick-capture models right from the dashboard.
- **Small Apps & Utilities:** Built-in widgets for quick daily actions (such as OTP generators, network tools, calendar integration, etc.).
- **Local First:** Everything is stored locally in JSON databases. No external databases, and no cloud-spying!

---

## 🚀 Installation & Setup

Installation is quick and easy. Follow these steps to perform a fresh launch of your application.

### Prerequisites
- Python 3.8+
- `pip` (Python package installer)

### Installation Steps

1. **Clone or Download the Repository**
   Ensure all files (including `app.py`, `requirements.txt`, `static/`, and `templates/`) are in your working directory.

2. **Create a Virtual Environment**
   Open your terminal and run the following command in the project directory:
   ```bash
   python3 -m venv venv
   ```

3. **Activate the Virtual Environment**
   - On Linux/macOS:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install Dependencies**
   Run the following command to install required packages:
   ```bash
   pip install -r requirements.txt
   ```

5. **Start the Application**
   Run the Flask server:
   ```bash
   python3 app.py
   ```

6. **Access the Dashboard**
   Open your web browser and navigate to:
   http://127.0.0.1:8000

## 📝 Notes
- `data.json` and `settings.json` will be automatically generated upon your first visit. These power the localized database storage.
- Customizations will be saved seamlessly to your local files.
