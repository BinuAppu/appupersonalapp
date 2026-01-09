document.addEventListener('DOMContentLoaded', () => {
    // Theme Logic
    window.setTheme = function (theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        // Update Settings Page Inputs if they exist
        const lightRadio = document.getElementById('settingsLightTheme');
        const darkRadio = document.getElementById('settingsDarkTheme');
        const schemeSelect = document.getElementById('colorSchemeSelect');

        if (lightRadio && darkRadio) {
            if (theme === 'light') lightRadio.checked = true;
            else if (theme === 'dark') darkRadio.checked = true;
            else {
                // If custom theme, uncheck both or keep as is? 
                // Unchecking both is cleaner to show "neither light nor dark standard" is active
                lightRadio.checked = false;
                darkRadio.checked = false;
            }
        }

        if (schemeSelect) {
            const validThemes = [
                'hackthebox', 'dracula', 'ocean',
                'solarized-light', 'solarized-dark',
                'monokai', 'nord',
                'gruvbox-light', 'gruvbox-dark',
                'cyberpunk', 'forest', 'sunset', 'midnight',
                'atom-one-dark', 'atom-one-light', 'ayu-dark', 'ayu-light', 'ayu-mirage',
                'base16-tomorrow-dark', 'base16-tomorrow-light', 'catppuccin-latte',
                'catppuccin-frappe', 'catppuccin-macchiato', 'catppuccin-mocha', 'cobalt2',
                'darcula', 'dracula-soft', 'github-dark', 'github-light', 'jellybeans',
                'material-darker', 'material-lighter', 'material-ocean', 'material-palenight',
                'monokai-pro', 'night-owl', 'shades-of-purple', 'synthwave-84',
                'tokyo-night', 'zenburn', 'solarized-ocean', 'deep-purple', 'matrix-green',
                'inferno-hacker'
            ];
            if (validThemes.includes(theme)) {
                schemeSelect.value = theme;
            } else {
                schemeSelect.value = 'default';
            }
        }
    }

    window.changeColorScheme = function (scheme) {
        if (scheme === 'default') {
            setTheme('light'); // Default fallback
        } else {
            setTheme(scheme);
        }
    }

    window.changeFontFamily = function (font) {
        document.body.style.fontFamily = font;
        localStorage.setItem('fontFamily', font);
    }

    // Init Theme and Font
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    const savedFont = localStorage.getItem('fontFamily');
    if (savedFont) {
        document.body.style.fontFamily = savedFont;
    }

    // Modal Logic
    const modal = document.getElementById("createModal");
    const editModal = document.getElementById("editModal");
    const commentsModal = document.getElementById("commentsModal");
    const kbModal = document.getElementById("kbModal");
    const kbResultModal = document.getElementById("kbResultDetailModal");
    const timeframeSlider = document.getElementById('timeframeSlider');
    const timeframeValue = document.getElementById('timeframeValue');

    if (timeframeSlider) {
        timeframeSlider.addEventListener('input', async (e) => {
            const weeks = e.target.value;
            timeframeValue.innerText = weeks;
            const res = await fetch(`/api/all_data?weeks=${weeks}`);
            const data = await res.json();
            updateReminderList(data.reminders, weeks);
        });
    }

    function updateReminderList(allReminders, weeks) {
        const reminderList = document.querySelector('.reminder-list');
        if (!reminderList) return;

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const endDate = new Date(today);
        endDate.setDate(today.getDate() + (weeks * 7));
        endDate.setHours(23, 59, 59, 999);

        const upcoming = [];
        allReminders.forEach(rem => {
            const remDate = new Date(rem.date + 'T00:00:00');
            let nextOccur = getNextOccurrence(remDate, rem.recurrence, today);

            if (nextOccur && nextOccur >= today && nextOccur <= endDate) {
                upcoming.push({
                    ...rem,
                    display_date: nextOccur.toISOString().split('T')[0]
                });
            }
        });

        upcoming.sort((a, b) => new Date(a.display_date) - new Date(b.display_date));

        if (upcoming.length > 0) {
            reminderList.innerHTML = upcoming.map(rem => `
                <div class="item-card recur-${rem.recurrence.toLowerCase()}" onclick="viewComments('reminder', '${rem.id}', '${rem.title.replace(/'/g, "\\'")}')">
                    <div class="item-card-header">
                        <div>
                            <h4 class="item-card-title">${rem.title}</h4>
                            <div class="item-card-meta">${rem.display_date} • ${rem.recurrence}</div>
                        </div>
                        <span class="delete-icon delete-btn" data-type="reminders" data-id="${rem.id}"
                            onclick="event.stopPropagation()">🗑️</span>
                    </div>
                </div>
            `).join('');
        }
    }

    function getNextOccurrence(startDate, recurrence, relativeTo) {
        let current = new Date(startDate);
        current.setHours(0, 0, 0, 0);
        let rel = new Date(relativeTo);
        rel.setHours(0, 0, 0, 0);
        if (recurrence === 'None') return current >= rel ? current : null;
        while (current < rel) {
            if (recurrence === 'Daily') current.setDate(current.getDate() + 1);
            else if (recurrence === 'Weekly') current.setDate(current.getDate() + 7);
            else if (recurrence === 'Monthly') {
                let d = current.getDate();
                current.setMonth(current.getMonth() + 1);
                if (current.getDate() != d) current.setDate(0);
            }
            else if (recurrence === 'Yearly') current.setFullYear(current.getFullYear() + 1);
        }
        return current;
    }

    window.openCreateModal = function (type) {
        modal.style.display = "block";
        const title = document.getElementById('modalTitle');
        if (type === 'reminder') {
            title.innerText = "New Reminder 🔔";
            showForm('reminder');
        } else {
            title.innerText = "New Task ✅";
            showForm('task');
        }
    }

    window.closeModal = function () {
        modal.style.display = "none";
        // Reset forms
        document.getElementById('reminderForm')?.reset();
        document.getElementById('taskForm')?.reset();
    }
    window.closeEditModal = function () {
        const editModal = document.getElementById('editModal');
        if (editModal) {
            editModal.style.display = "none";
        }
        // Reset forms
        const editReminderForm = document.getElementById('editReminderForm');
        const editTaskForm = document.getElementById('editTaskForm');
        if (editReminderForm) {
            editReminderForm.reset();
            editReminderForm.style.display = 'none';
        }
        if (editTaskForm) {
            editTaskForm.reset();
            editTaskForm.style.display = 'none';
        }
        // Clear hidden ID fields
        const editRemId = document.getElementById('editRemId');
        const editTaskId = document.getElementById('editTaskId');
        if (editRemId) editRemId.value = '';
        if (editTaskId) editTaskId.value = '';
    }
    window.closeCommentsModal = function () {
        commentsModal.style.display = "none";
        document.getElementById('newCommentInput').value = '';
    }
    window.closeKBModal = function () { kbModal.style.display = "none"; }
    window.closeKBResultModal = function () { kbResultModal.style.display = "none"; }

    window.onclick = function (event) {
        if (event.target == modal) modal.style.display = "none";
        if (event.target == editModal) editModal.style.display = "none";
        if (event.target == commentsModal) commentsModal.style.display = "none";
        if (event.target == kbModal) kbModal.style.display = "none";
        if (event.target == kbResultModal) kbResultModal.style.display = "none";
    }

    window.showForm = function (type) {
        if (type === 'reminder') {
            document.getElementById('reminderForm').style.display = 'block';
            document.getElementById('taskForm').style.display = 'none';
        } else {
            document.getElementById('reminderForm').style.display = 'none';
            document.getElementById('taskForm').style.display = 'block';
        }
    }

    // --- Knowledge Base Modern Logic ---
    let currentKBResults = [];

    window.searchKB = async function () {
        const input = document.getElementById('kbSearchInput');
        const resultsContainer = document.getElementById('kbSearchResults');
        const query = input.value.trim();

        if (!query) {
            resultsContainer.innerHTML = '';
            return;
        }

        const res = await fetch(`/api/kb/search?q=${encodeURIComponent(query)}`);
        const items = await res.json();
        currentKBResults = items;

        if (items.length > 0) {
            resultsContainer.innerHTML = items.map(item => {
                // Create a temporary div to extract text from HTML
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = item.data;
                const textContent = tempDiv.textContent || tempDiv.innerText || '';
                const snippet = textContent.substring(0, 200) + (textContent.length > 200 ? '...' : '');

                return `
                <div class="kb-modern-result-item">
                    <span class="kb-modern-result-title" onclick="openKBResultModal('${item.id}')">${item.title}</span>
                    <div class="kb-modern-result-snippet">${snippet}</div>
                </div>
            `}).join('');
        } else {
            resultsContainer.innerHTML = '<p style="text-align: center; color: var(--text-muted);">No matching results found.</p>';
        }
    }

    window.openKBResultModal = function (id) {
        const item = currentKBResults.find(i => i.id === id);
        if (!item) return;

        document.getElementById('kbResultDetailTitle').innerText = item.title;
        // Display HTML content properly
        document.getElementById('kbResultDetailData').innerHTML = item.data;
        document.getElementById('kbResultDetailDate').innerText = `Created on ${new Date(item.created_at).toLocaleDateString()}`;

        const linkBtn = document.getElementById('kbResultDetailLink');
        if (item.url) {
            linkBtn.href = item.url;
            linkBtn.parentElement.style.display = 'block';
        } else {
            linkBtn.parentElement.style.display = 'none';
        }

        kbResultModal.style.display = "block";
    }

    window.openKBModal = async function (id = null) {
        const titleEm = document.getElementById('kbModalTitle');
        const form = document.getElementById('kbForm');
        const kbDataElement = document.getElementById('kbData');

        // Reset form and clear content
        document.getElementById('kbTitle').value = '';
        document.getElementById('kbUrl').value = '';
        document.getElementById('kbId').value = '';

        // Handle both textarea and contenteditable div
        if (kbDataElement.tagName === 'TEXTAREA') {
            kbDataElement.value = '';
        } else {
            kbDataElement.innerHTML = '';
        }

        if (id) {
            titleEm.innerText = "Edit Knowledge Base";
            // Fetch the item to populate the form
            const res = await fetch('/api/kb');
            const items = await res.json();
            const item = items.find(i => i.id === id);
            if (item) {
                document.getElementById('kbTitle').value = item.title;
                document.getElementById('kbUrl').value = item.url || '';
                document.getElementById('kbId').value = item.id;
                if (kbDataElement.tagName === 'TEXTAREA') {
                    kbDataElement.value = item.data;
                } else {
                    kbDataElement.innerHTML = item.data;
                }
            }
        } else {
            titleEm.innerText = "New Knowledge Base";
        }
        kbModal.style.display = "block";
    }

    document.getElementById('kbForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('kbId').value;
        const kbDataElement = document.getElementById('kbData');
        // Handle both textarea and contenteditable div
        const dataContent = kbDataElement.tagName === 'TEXTAREA'
            ? kbDataElement.value
            : kbDataElement.innerHTML;
        const data = {
            title: document.getElementById('kbTitle').value,
            data: dataContent,
            url: document.getElementById('kbUrl').value
        };
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/kb/${id}` : '/api/kb';
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            closeKBModal();
            // Only call searchKB if we're on the knowledge base page
            if (window.location.pathname === '/knowledge' && typeof searchKB === 'function') {
                searchKB();
            }
            // If on list_view, reload
            if (window.location.pathname === '/all') window.location.reload();
        } else {
            alert('Failed to save knowledge base item');
        }
    });


    window.deleteKBItem = async function (id) {
        if (!confirm("Are you sure you want to delete this item?")) return;
        const res = await fetch(`/api/kb/${id}`, { method: 'DELETE' });
        if (res.ok) {
            if (window.location.pathname === '/all') window.location.reload();
            else searchKB();
        }
    }

    // View Comments Logic
    window.viewComments = async function (itemType, itemId, itemTitle) {
        const commentsList = document.getElementById('commentsList');
        const modalTitle = document.getElementById('commentsModalTitle');
        const submitBtn = document.getElementById('submitCommentBtn');
        const input = document.getElementById('newCommentInput');
        modalTitle.innerText = `Comments: ${itemTitle}`;
        commentsList.innerHTML = '<p style="text-align:center;">Loading...</p>';
        commentsModal.style.display = "block";
        const res = await fetch('/api/all_data');
        const data = await res.json();
        const items = itemType === 'task' ? data.tasks : data.reminders;
        const item = items.find(i => i.id === itemId);
        if (item) {
            commentsList.innerHTML = '';
            if (item.comments && item.comments.length > 0) {
                item.comments.forEach(c => {
                    const date = new Date(c.timestamp).toLocaleString();
                    const div = document.createElement('div');
                    div.className = 'comment-entry';
                    div.innerHTML = `<div class="comment-time">${date}</div><div>${c.text}</div>`;
                    commentsList.appendChild(div);
                });
            }
        }
        // Clear input
        input.value = '';
        // Set up event handlers
        submitBtn.onclick = () => submitComment(itemType, itemId, 'newCommentInput', itemTitle);
        input.onkeypress = (e) => {
            if (e.key === 'Enter') {
                submitComment(itemType, itemId, 'newCommentInput', itemTitle);
            }
        };
    }

    // Submit Comment Function
    window.submitComment = async function (itemType, itemId, inputId, itemTitle) {
        const input = document.getElementById(inputId);
        const text = input.value.trim();
        if (!text) {
            alert('Please enter a comment');
            return;
        }

        const res = await fetch('/api/comments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                item_type: itemType,
                item_id: itemId,
                text: text
            })
        });

        if (res.ok) {
            input.value = '';
            // Reload comments
            await viewComments(itemType, itemId, itemTitle);
            // Reload page if on dashboard or all items page
            if (window.location.pathname === '/' || window.location.pathname === '/all') {
                window.location.reload();
            }
        } else {
            alert('Failed to add comment');
        }
    }

    // Open Edit Modal Function - Ensure it's always available
    if (typeof window.openEditModal === 'undefined') {
        window.openEditModal = function () { };
    }

    window.openEditModal = function (type, id, title, description, dateOrStatus, recurrence = null) {
        // Ensure function is called
        if (!type || !id) {
            console.error('openEditModal called with invalid parameters:', { type, id });
            return false;
        }
        // Get all required elements
        const editModal = document.getElementById('editModal');
        const editModalTitle = document.getElementById('editModalTitle');
        const editReminderForm = document.getElementById('editReminderForm');
        const editTaskForm = document.getElementById('editTaskForm');
        const editRemId = document.getElementById('editRemId');
        const editTaskId = document.getElementById('editTaskId');

        // Validate required elements exist
        if (!editModal) {
            console.error('Edit modal element not found');
            alert('Edit modal not found. Please refresh the page.');
            return false;
        }

        if (!editModalTitle) {
            console.error('Edit modal title element not found');
            return false;
        }

        // Ensure modal is closed and reset first
        editModal.style.display = "none";

        // Reset and hide both forms
        if (editReminderForm) {
            editReminderForm.reset();
            editReminderForm.style.display = 'none';
        }
        if (editTaskForm) {
            editTaskForm.reset();
            editTaskForm.style.display = 'none';
        }

        // Clear ID fields
        if (editRemId) editRemId.value = '';
        if (editTaskId) editTaskId.value = '';

        // Handle reminder editing
        if (type === 'reminder') {
            if (!editReminderForm) {
                console.error('Edit reminder form not found');
                return false;
            }

            editModalTitle.innerText = 'Edit Reminder';
            editReminderForm.style.display = 'block';
            if (editTaskForm) editTaskForm.style.display = 'none';

            // Set form values
            if (editRemId) editRemId.value = String(id || '');

            const titleField = document.getElementById('editRemTitle');
            const descField = document.getElementById('editRemDesc');
            const dateField = document.getElementById('editRemDate');
            const recurField = document.getElementById('editRemRecur');

            if (titleField) titleField.value = String(title || '').replace(/\\'/g, "'");
            if (descField) descField.value = String(description || '').replace(/\\'/g, "'");
            if (dateField) dateField.value = String(dateOrStatus || '');
            if (recurField) recurField.value = String(recurrence || 'None');

            // Handle task editing
        } else if (type === 'task') {
            if (!editTaskForm) {
                console.error('Edit task form not found');
                return false;
            }

            editModalTitle.innerText = 'Edit Task';
            if (editReminderForm) editReminderForm.style.display = 'none';
            editTaskForm.style.display = 'block';

            // Set form values
            if (editTaskId) editTaskId.value = String(id || '');

            const titleField = document.getElementById('editTaskTitle');
            const descField = document.getElementById('editTaskDesc');
            const statusField = document.getElementById('editTaskStatus');

            if (titleField) titleField.value = String(title || '').replace(/\\'/g, "'");
            if (descField) descField.value = String(description || '').replace(/\\'/g, "'");
            if (statusField) statusField.value = String(dateOrStatus || 'Yet to Start');

        } else {
            console.error('Invalid edit type:', type);
            return false;
        }

        // Show the modal and ensure it's visible
        editModal.style.display = "block";
        editModal.style.visibility = "visible";
        editModal.style.opacity = "1";

        // Force a reflow to ensure the display change takes effect
        void editModal.offsetHeight;

        return true;
    }

    // Form Submission Handlers
    document.getElementById('reminderForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            title: document.getElementById('remTitle').value,
            description: document.getElementById('remDesc').value,
            date: document.getElementById('remDate').value,
            recurrence: document.getElementById('remRecur').value
        };
        const res = await fetch('/api/reminders', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            closeModal();
            // Save current tab before reload
            if (window.location.pathname === '/all') {
                const activeTab = document.querySelector('.tab-btn.active')?.id;
                if (activeTab) {
                    localStorage.setItem('activeTab', activeTab === 'reminderTabBtn' ? 'reminders' : activeTab === 'taskTabBtn' ? 'tasks' : 'kb');
                }
            }
            window.location.reload();
        } else {
            alert('Failed to create reminder');
        }
    });

    document.getElementById('taskForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            title: document.getElementById('taskTitle').value,
            description: document.getElementById('taskDesc').value,
            status: document.getElementById('taskStatus').value
        };
        const res = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            closeModal();
            // Save current tab before reload
            if (window.location.pathname === '/all') {
                const activeTab = document.querySelector('.tab-btn.active')?.id;
                if (activeTab) {
                    localStorage.setItem('activeTab', activeTab === 'reminderTabBtn' ? 'tasks' : activeTab === 'taskTabBtn' ? 'tasks' : 'kb');
                }
            }
            window.location.reload();
        } else {
            alert('Failed to create task');
        }
    });

    // Edit Form Submission Handlers
    document.getElementById('editReminderForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = document.getElementById('editRemId').value;
        if (!id) {
            alert('Invalid reminder ID');
            return;
        }

        const data = {
            title: document.getElementById('editRemTitle').value,
            description: document.getElementById('editRemDesc').value,
            date: document.getElementById('editRemDate').value,
            recurrence: document.getElementById('editRemRecur').value
        };

        try {
            const res = await fetch(`/api/reminders/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                closeEditModal();
                // Save current tab before reload
                if (window.location.pathname === '/all') {
                    const activeTab = document.querySelector('.tab-btn.active')?.id;
                    if (activeTab) {
                        localStorage.setItem('activeTab', activeTab === 'reminderTabBtn' ? 'reminders' : activeTab === 'taskTabBtn' ? 'tasks' : 'kb');
                    }
                }
                window.location.reload();
            } else {
                const errorData = await res.json().catch(() => ({}));
                alert('Failed to update reminder: ' + (errorData.message || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error updating reminder:', error);
            alert('Failed to update reminder: ' + error.message);
        }
    });

    document.getElementById('editTaskForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const id = document.getElementById('editTaskId').value;
        if (!id) {
            alert('Invalid task ID');
            return;
        }

        const data = {
            title: document.getElementById('editTaskTitle').value,
            description: document.getElementById('editTaskDesc').value,
            status: document.getElementById('editTaskStatus').value
        };

        try {
            const res = await fetch(`/api/tasks/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                closeEditModal();
                // Save current tab before reload
                if (window.location.pathname === '/all') {
                    const activeTab = document.querySelector('.tab-btn.active')?.id;
                    if (activeTab) {
                        localStorage.setItem('activeTab', activeTab === 'reminderTabBtn' ? 'reminders' : activeTab === 'taskTabBtn' ? 'tasks' : 'kb');
                    }
                }
                window.location.reload();
            } else {
                const errorData = await res.json().catch(() => ({}));
                alert('Failed to update task: ' + (errorData.message || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error updating task:', error);
            alert('Failed to update task: ' + error.message);
        }
    });

    // Edit and Delete Button Event Handlers (Event Delegation)
    document.addEventListener('click', async (e) => {
        // Handle Edit buttons using data attributes
        if (e.target.classList.contains('edit-btn') || e.target.closest('.edit-btn')) {
            const btn = e.target.classList.contains('edit-btn') ? e.target : e.target.closest('.edit-btn');

            // Check if button has data attributes (new approach)
            const editType = btn.getAttribute('data-edit-type');
            const editId = btn.getAttribute('data-edit-id');

            if (editType && editId) {
                e.preventDefault();
                e.stopPropagation();

                const title = btn.getAttribute('data-edit-title') || '';
                const description = btn.getAttribute('data-edit-description') || '';

                if (editType === 'task') {
                    const status = btn.getAttribute('data-edit-status') || 'Yet to Start';
                    openEditModal('task', editId, title, description, status);
                } else if (editType === 'reminder') {
                    const date = btn.getAttribute('data-edit-date') || '';
                    const recurrence = btn.getAttribute('data-edit-recurrence') || 'None';
                    openEditModal('reminder', editId, title, description, date, recurrence);
                }
                return;
            }

            // Fallback: Check if button has onclick attribute (old inline handler)
            const onclickAttr = btn.getAttribute('onclick');
            if (onclickAttr && onclickAttr.includes('openEditModal')) {
                // Let the inline handler work for backward compatibility
                return;
            }
        }

        // Handle Delete buttons
        if (e.target.classList.contains('delete-btn') || e.target.closest('.delete-btn')) {
            const btn = e.target.classList.contains('delete-btn') ? e.target : e.target.closest('.delete-btn');
            const itemType = btn.getAttribute('data-type');
            const itemId = btn.getAttribute('data-id');

            if (!itemId || !itemType) return;

            // Prevent event from triggering delete if it's inside an edit button context
            if (btn.closest('.edit-btn')) return;

            if (!confirm('Are you sure you want to delete this item?')) return;

            let endpoint = '';
            if (itemType === 'reminders') {
                endpoint = `/api/reminders/${itemId}`;
            } else if (itemType === 'tasks') {
                endpoint = `/api/tasks/${itemId}`;
            } else {
                return;
            }

            const res = await fetch(endpoint, { method: 'DELETE' });
            if (res.ok) {
                // Save current tab before reload
                if (window.location.pathname === '/all') {
                    const activeTab = document.querySelector('.tab-btn.active')?.id;
                    if (activeTab) {
                        localStorage.setItem('activeTab', activeTab === 'reminderTabBtn' ? 'reminders' : activeTab === 'taskTabBtn' ? 'tasks' : 'kb');
                    }
                }
                window.location.reload();
            } else {
                alert('Failed to delete item');
            }
        }
    });

    // Restore active tab on page load (for /all page)
    if (window.location.pathname === '/all') {
        const savedTab = localStorage.getItem('activeTab');
        if (savedTab) {
            // Wait for page to fully load, including inline scripts
            setTimeout(() => {
                if (typeof window.showTab === 'function') {
                    window.showTab(savedTab);
                } else {
                    // Fallback: try again after a longer delay
                    setTimeout(() => {
                        if (typeof window.showTab === 'function') {
                            window.showTab(savedTab);
                        }
                    }, 200);
                }
            }, 150);
        }
    }

    // Copy to Clipboard Function for Knowledge Base
    window.copyKBContent = async function (event) {
        event.preventDefault();
        const dataElement = document.getElementById('kbResultDetailData');
        if (!dataElement) return;

        // Get text content (strip HTML tags for plain text copy)
        const textContent = dataElement.innerText || dataElement.textContent || '';

        try {
            // Try modern clipboard API first
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(textContent);
                // Show feedback
                const btn = event.target.closest('button') || event.target;
                const originalText = btn.innerHTML;
                btn.innerHTML = '✓ Copied!';
                btn.style.backgroundColor = 'var(--success-color, #4CAF50)';
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.backgroundColor = '';
                }, 2000);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = textContent;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);

                // Show feedback
                const btn = event.target.closest('button') || event.target;
                const originalText = btn.innerHTML;
                btn.innerHTML = '✓ Copied!';
                btn.style.backgroundColor = 'var(--success-color, #4CAF50)';
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.backgroundColor = '';
                }, 2000);
            }
        } catch (err) {
            console.error('Failed to copy:', err);
            alert('Failed to copy to clipboard. Please select and copy manually.');
        }
    };
    // --- Secure Vault Logic ---
    let currentMasterKey = null;

    window.unlockVault = async function () {
        const key = document.getElementById('master-key-input').value;
        if (!key) return;

        // Try validation
        const res = await fetch('/api/secure/validate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ master_key: key })
        });
        const data = await res.json();

        if (data.valid) {
            currentMasterKey = key;
            showVault();
        } else {
            const msgObj = document.getElementById('unlock-message');
            msgObj.innerText = "Invalid Master Key";
            msgObj.style.color = "red";
        }
    }

    window.createVault = async function () {
        const key = document.getElementById('new-master-key').value;
        const confirmKey = document.getElementById('confirm-master-key').value;
        const msg = document.getElementById('unlock-message');

        if (!key || !confirmKey) {
            msg.innerText = "Please fill in all fields.";
            return;
        }

        if (key !== confirmKey) {
            msg.innerText = "Passwords do not match.";
            return;
        }

        if (key.length < 4) {
            msg.innerText = "Password is too short.";
            return;
        }

        const res = await fetch('/api/secure/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ master_key: key })
        });
        const data = await res.json();

        if (data.success) {
            currentMasterKey = key;
            showVault();
        } else {
            msg.innerText = data.error || "Failed to create vault.";
        }
    }

    window.lockVault = function () {
        currentMasterKey = null;
        // Reload page to reset state
        location.reload();
    }

    window.showVault = async function () {
        document.getElementById('unlock-screen').style.display = 'none';
        document.getElementById('vault-view').style.display = 'block';
        loadSecureItems();
    }

    let secureItemsCache = []; // Cache items for search

    window.loadSecureItems = async function () {
        const res = await fetch('/api/secure/items', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ master_key: currentMasterKey })
        });
        if (!res.ok) {
            lockVault(); // Session expired/invalid
            return;
        }
        secureItemsCache = await res.json();
        renderSecureTable(secureItemsCache);
    }

    window.searchSecureItems = function () {
        const query = document.getElementById('secure-search').value.toLowerCase();
        const filtered = secureItemsCache.filter(item =>
            (item.title && item.title.toLowerCase().includes(query)) ||
            (item.user_id && item.user_id.toLowerCase().includes(query)) ||
            (item.notes && item.notes.toLowerCase().includes(query))
        );
        renderSecureTable(filtered);
    }

    function renderSecureTable(items) {
        const list = document.getElementById('secure-items-list');
        if (items.length === 0) {
            list.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--text-secondary); padding: 20px;">No secrets found.</td></tr>';
        } else {
            list.innerHTML = items.map(item => `
                <tr>
                    <td><div style="font-weight:bold;">${escapeHtml(item.title)}</div></td>
                    <td>${escapeHtml(item.user_id)}</td>
                    <td><span class="password-cell">***</span></td>
                    <td><a href="${item.url}" target="_blank" style="color:var(--accent-color); text-decoration:none;">${escapeHtml(item.url)}</a></td>
                    <td><div style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(item.notes)}">${escapeHtml(item.notes)}</div></td>
                    <td>
                        <div class="action-buttons">
                            <button class="action-btn btn-copy-user" title="Copy Username" onclick="copyToClipboard('${escapeHtml(item.user_id)}')">
                                <i class="fas fa-user-copy"></i>
                            </button>
                            <button class="action-btn btn-copy-pass" title="Copy Password" onclick="copyToClipboard('${escapeHtml(item.password)}')">
                                <i class="fas fa-key"></i>
                            </button>
                            <button class="action-btn btn-edit" title="Edit" onclick="openSecureModal('${item.id}')">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="action-btn btn-delete" title="Delete" onclick="deleteSecureItem('${item.id}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    }

    window.copyToClipboard = function (text) {
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            const el = document.createElement('div');
            el.innerText = "Copied!";
            el.style.position = 'fixed';
            el.style.bottom = '20px';
            el.style.left = '50%';
            el.style.transform = 'translateX(-50%)';
            el.style.background = 'rgba(0,0,0,0.7)';
            el.style.color = 'white';
            el.style.padding = '10px 20px';
            el.style.borderRadius = '5px';
            el.style.zIndex = '9999';
            document.body.appendChild(el);
            setTimeout(() => document.body.removeChild(el), 1500);
        });
    }

    // Modal
    window.openSecureModal = function (id = null) {
        document.getElementById('secure-modal').style.display = 'block';
        const titleEl = document.getElementById('secure-modal-title');

        let item = { title: '', user_id: '', password: '', url: '', notes: '' };

        if (id) {
            titleEl.innerText = 'Edit Secret';
            // Find item in cache
            item = secureItemsCache.find(i => i.id === id) || item;
        } else {
            titleEl.innerText = 'Add Secret';
        }

        document.getElementById('secure-id').value = id || '';
        document.getElementById('secure-title').value = item.title;
        document.getElementById('secure-user-id').value = item.user_id;
        document.getElementById('secure-password').value = item.password;
        document.getElementById('secure-url').value = item.url;
        document.getElementById('secure-notes').value = item.notes;
    }

    window.closeSecureModal = function () {
        document.getElementById('secure-modal').style.display = 'none';
    }

    window.saveSecureItem = async function () {
        const id = document.getElementById('secure-id').value;
        const item = {
            title: document.getElementById('secure-title').value,
            user_id: document.getElementById('secure-user-id').value,
            password: document.getElementById('secure-password').value,
            url: document.getElementById('secure-url').value,
            notes: document.getElementById('secure-notes').value
        };

        if (!item.title || !item.password) {
            alert("Title and Password are required");
            return;
        }

        const endpoint = id ? `/api/secure/${id}` : '/api/secure/add';
        const method = id ? 'PUT' : 'POST';

        const res = await fetch(endpoint, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ master_key: currentMasterKey, item: item })
        });

        if (res.ok) {
            closeSecureModal();
            loadSecureItems();
        } else {
            alert("Failed to save item");
        }
    }

    window.deleteSecureItem = async function (id) {
        if (!confirm("Are you sure?")) return;
        const res = await fetch(`/api/secure/${id}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ master_key: currentMasterKey })
        });
        if (res.ok) {
            loadSecureItems();
        }
    }

    window.togglePasswordVisibility = function (id) {
        const el = document.getElementById(id);
        if (el.type === 'password') {
            el.type = 'text';
        } else {
            el.type = 'password';
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        return text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // --- Password Generator Logic ---
    window.generatePassword = function () {
        const length = document.getElementById('pg-length').value;
        const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@$-[]:";
        let password = "";
        const array = new Uint32Array(length);
        window.crypto.getRandomValues(array);

        for (let i = 0; i < length; i++) {
            password += charset[array[i] % charset.length];
        }

        document.getElementById('pg-output').value = password;
    }

    window.copyGeneratedPassword = function () {
        const pw = document.getElementById('pg-output').value;
        if (pw) {
            window.copyToClipboard(pw);
        }
    }

    // Initialize logic if elements exist
    if (document.getElementById('pg-length')) {
        document.getElementById('pg-length').addEventListener('input', function () {
            document.getElementById('pg-length-val').innerText = this.value;
        });
    }

    // Subtask toggle function
    window.toggleSubtask = function (element) {
        const subtaskItem = element.closest('.subtask-item');
        const nestedSubtasks = subtaskItem.querySelector('.subtask-nested');
        if (!nestedSubtasks) return;

        const isExpanded = element.getAttribute('data-expanded') === 'true';

        if (isExpanded) {
            nestedSubtasks.style.display = 'none';
            element.textContent = '▶';
            element.setAttribute('data-expanded', 'false');
        } else {
            nestedSubtasks.style.display = 'block';
            element.textContent = '▼';
            element.setAttribute('data-expanded', 'true');
        }
    }

    // Dashboard arrangement functions
    window.moveSection = function (sectionType, direction) {
        const sections = ['tasks', 'reminders', 'projects'];
        const currentIndex = sections.indexOf(sectionType);
        if (currentIndex === -1) return;

        let newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
        if (newIndex < 0 || newIndex >= sections.length) return;

        const currentSection = document.querySelector(`[data-section="${sectionType}"]`);
        const targetSection = document.querySelector(`[data-section="${sections[newIndex]}"]`);

        if (currentSection && targetSection) {
            if (direction === 'up') {
                currentSection.parentNode.insertBefore(currentSection, targetSection);
            } else {
                currentSection.parentNode.insertBefore(currentSection, targetSection.nextSibling);
            }

            // Save order to localStorage
            const newOrder = Array.from(document.querySelectorAll('.section-container')).map(s => s.getAttribute('data-section'));
            localStorage.setItem('dashboardSectionOrder', JSON.stringify(newOrder));
        }
    }

    window.moveItem = function (itemType, itemId, direction) {
        const container = document.querySelector(`[data-sortable="${itemType}s"]`);
        if (!container) return;

        const items = Array.from(container.querySelectorAll(`[data-item-type="${itemType}"]`));
        const currentIndex = items.findIndex(item => item.getAttribute('data-item-id') === itemId);

        if (currentIndex === -1) return;

        let newIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
        if (newIndex < 0 || newIndex >= items.length) return;

        const currentItem = items[currentIndex];
        const targetItem = items[newIndex];

        if (direction === 'up') {
            container.insertBefore(currentItem, targetItem);
        } else {
            container.insertBefore(currentItem, targetItem.nextSibling);
        }

        // Save order to localStorage
        const itemOrder = Array.from(container.querySelectorAll(`[data-item-type="${itemType}"]`)).map(item => item.getAttribute('data-item-id'));
        localStorage.setItem(`dashboard${itemType}sOrder`, JSON.stringify(itemOrder));
    }

    // Restore dashboard order on load
    if (window.location.pathname === '/') {
        const savedSectionOrder = localStorage.getItem('dashboardSectionOrder');
        if (savedSectionOrder) {
            try {
                const order = JSON.parse(savedSectionOrder);
                const sections = document.querySelectorAll('.section-container');
                const sectionMap = {};
                sections.forEach(s => {
                    sectionMap[s.getAttribute('data-section')] = s;
                });

                const dashboardGrid = document.querySelector('.dashboard-grid');
                if (dashboardGrid) {
                    order.forEach(sectionType => {
                        if (sectionMap[sectionType]) {
                            dashboardGrid.appendChild(sectionMap[sectionType]);
                        }
                    });
                }
            } catch (e) {
                console.error('Error restoring section order:', e);
            }
        }

        // Restore item orders
        ['task', 'reminder', 'project'].forEach(itemType => {
            const savedOrder = localStorage.getItem(`dashboard${itemType}sOrder`);
            if (savedOrder) {
                try {
                    const order = JSON.parse(savedOrder);
                    const container = document.querySelector(`[data-sortable="${itemType}s"]`);
                    if (!container) return;

                    const items = Array.from(container.querySelectorAll(`[data-item-type="${itemType}"]`));
                    const itemMap = {};
                    items.forEach(item => {
                        itemMap[item.getAttribute('data-item-id')] = item;
                    });

                    order.forEach(itemId => {
                        if (itemMap[itemId]) {
                            container.appendChild(itemMap[itemId]);
                        }
                    });
                } catch (e) {
                    console.error(`Error restoring ${itemType} order:`, e);
                }
            }
        });
    }

    // --- Projects Logic ---
    const projectModal = document.getElementById('projectModal');
    const projectTaskModal = document.getElementById('projectTaskModal');
    const projectTaskCommentsModal = document.getElementById('projectTaskCommentsModal');

    window.openCreateProjectModal = function () {
        if (!projectModal) return;
        document.getElementById('projectModalTitle').innerText = 'New Project';
        document.getElementById('projectForm').reset();
        document.getElementById('projectId').value = '';
        projectModal.style.display = 'block';
    }

    window.openEditProjectModal = function (id, name, description, startDate, endDate, status) {
        if (!projectModal) return;
        document.getElementById('projectModalTitle').innerText = 'Edit Project';
        document.getElementById('projectId').value = id;
        document.getElementById('projectName').value = name;
        document.getElementById('projectDescription').value = description;
        document.getElementById('projectStartDate').value = startDate;
        document.getElementById('projectEndDate').value = endDate;
        document.getElementById('projectStatus').value = status;
        projectModal.style.display = 'block';
    }

    window.closeProjectModal = function () {
        if (!projectModal) return;
        projectModal.style.display = 'none';
        document.getElementById('projectForm').reset();
    }

    window.openCreateProjectTaskModal = async function (projectId, parentId = null) {
        if (!projectTaskModal) return;
        document.getElementById('projectTaskModalTitle').innerText = parentId ? 'New Subtask' : 'New Task';
        document.getElementById('projectTaskForm').reset();
        document.getElementById('projectTaskProjectId').value = projectId;
        document.getElementById('projectTaskTaskId').value = '';
        document.getElementById('projectTaskParentId').value = parentId || '';
        document.getElementById('projectTaskStatusGroup').style.display = 'none';

        // Get date constraints - if parentId exists, fetch parent task dates, otherwise use project dates
        let minStartDate = window.projectStartDate;
        let maxEndDate = window.projectEndDate;

        if (parentId) {
            try {
                const res = await fetch(`/api/projects/${projectId}/tasks/${parentId}/parent-dates`);
                if (res.ok) {
                    const data = await res.json();
                    minStartDate = data.start_date;
                    maxEndDate = data.end_date;
                }
            } catch (e) {
                console.error('Error fetching parent dates:', e);
            }
        }

        // Set date constraints
        if (minStartDate && maxEndDate) {
            const startDateInput = document.getElementById('projectTaskStartDate');
            const endDateInput = document.getElementById('projectTaskEndDate');
            startDateInput.min = minStartDate;
            startDateInput.max = maxEndDate;
            endDateInput.min = minStartDate;
            endDateInput.max = maxEndDate;
        }

        projectTaskModal.style.display = 'block';
    }

    window.openCreateSubtaskModal = function (projectId, parentId) {
        openCreateProjectTaskModal(projectId, parentId);
    }

    window.openEditProjectTaskModal = function (projectId, taskId, name, comments, startDate, endDate, status, parentStartDate, parentEndDate) {
        if (!projectTaskModal) return;
        document.getElementById('projectTaskModalTitle').innerText = 'Edit Task';
        document.getElementById('projectTaskProjectId').value = projectId;
        document.getElementById('projectTaskTaskId').value = taskId;
        document.getElementById('projectTaskParentId').value = '';
        document.getElementById('projectTaskName').value = name;
        document.getElementById('projectTaskComments').value = comments;
        document.getElementById('projectTaskStartDate').value = startDate;
        document.getElementById('projectTaskEndDate').value = endDate;
        document.getElementById('projectTaskStatus').value = status;
        document.getElementById('projectTaskStatusGroup').style.display = 'block';

        // Set date constraints - use parent dates if provided (for subtasks), otherwise project dates
        const minStartDate = parentStartDate || window.projectStartDate;
        const maxEndDate = parentEndDate || window.projectEndDate;

        if (minStartDate && maxEndDate) {
            const startDateInput = document.getElementById('projectTaskStartDate');
            const endDateInput = document.getElementById('projectTaskEndDate');
            startDateInput.min = minStartDate;
            startDateInput.max = maxEndDate;
            endDateInput.min = minStartDate;
            endDateInput.max = maxEndDate;
        }

        projectTaskModal.style.display = 'block';
    }

    window.closeProjectTaskModal = function () {
        if (!projectTaskModal) return;
        projectTaskModal.style.display = 'none';
        document.getElementById('projectTaskForm').reset();
    }

    window.viewProjectTaskComments = async function (projectId, taskId, taskName) {
        if (!projectTaskCommentsModal) return;
        const commentsList = document.getElementById('projectTaskCommentsList');
        const modalTitle = document.getElementById('projectTaskCommentsModalTitle');
        const submitBtn = document.getElementById('submitProjectTaskCommentBtn');
        const input = document.getElementById('newProjectTaskCommentInput');

        modalTitle.innerText = `Comments: ${taskName}`;
        commentsList.innerHTML = '<p style="text-align:center;">Loading...</p>';
        projectTaskCommentsModal.style.display = 'block';

        const res = await fetch(`/api/projects/${projectId}`);
        const project = await res.json();
        const task = findTaskInTree(project.tasks, taskId);

        if (task) {
            commentsList.innerHTML = '';
            if (task.task_comments && task.task_comments.length > 0) {
                task.task_comments.forEach(c => {
                    const date = new Date(c.timestamp).toLocaleString();
                    const div = document.createElement('div');
                    div.className = 'comment-entry';
                    div.innerHTML = `<div class="comment-time">${date}</div><div>${c.text}</div>`;
                    commentsList.appendChild(div);
                });
            } else {
                commentsList.innerHTML = '<p style="text-align:center; color: var(--text-muted);">No comments yet.</p>';
            }
        }

        input.value = '';
        submitBtn.onclick = () => submitProjectTaskComment(projectId, taskId, taskName);
        input.onkeypress = (e) => {
            if (e.key === 'Enter') {
                submitProjectTaskComment(projectId, taskId, taskName);
            }
        };
    }

    function findTaskInTree(tasks, taskId) {
        for (const task of tasks) {
            if (task.id === taskId) return task;
            if (task.subtasks) {
                const found = findTaskInTree(task.subtasks, taskId);
                if (found) return found;
            }
        }
        return null;
    }

    window.submitProjectTaskComment = async function (projectId, taskId, taskName) {
        const input = document.getElementById('newProjectTaskCommentInput');
        const text = input.value.trim();
        if (!text) {
            alert('Please enter a comment');
            return;
        }

        const res = await fetch(`/api/projects/${projectId}/tasks/${taskId}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });

        if (res.ok) {
            input.value = '';
            await viewProjectTaskComments(projectId, taskId, taskName);
        } else {
            alert('Failed to add comment');
        }
    }

    window.closeProjectTaskCommentsModal = function () {
        if (!projectTaskCommentsModal) return;
        projectTaskCommentsModal.style.display = 'none';
        document.getElementById('newProjectTaskCommentInput').value = '';
    }

    window.toggleTask = function (element) {
        const taskItem = element.closest('.task-item');
        const subtasks = taskItem.querySelector('.task-subtasks');
        const isExpanded = element.getAttribute('data-expanded') === 'true';

        if (isExpanded) {
            subtasks.style.display = 'none';
            element.textContent = '▶';
            element.setAttribute('data-expanded', 'false');
        } else {
            subtasks.style.display = 'block';
            element.textContent = '▼';
            element.setAttribute('data-expanded', 'true');
        }
    }

    // Project form submission
    document.getElementById('projectForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('projectId').value;
        const data = {
            name: document.getElementById('projectName').value,
            description: document.getElementById('projectDescription').value,
            start_date: document.getElementById('projectStartDate').value,
            end_date: document.getElementById('projectEndDate').value,
            status: document.getElementById('projectStatus').value
        };

        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/projects/${id}` : '/api/projects';

        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await res.json();
        if (res.ok) {
            closeProjectModal();
            window.location.reload();
        } else {
            alert(result.error || 'Failed to save project');
        }
    });

    // Project task form submission
    document.getElementById('projectTaskForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const projectId = document.getElementById('projectTaskProjectId').value;
        const taskId = document.getElementById('projectTaskTaskId').value;
        const parentId = document.getElementById('projectTaskParentId').value;
        const data = {
            name: document.getElementById('projectTaskName').value,
            comments: document.getElementById('projectTaskComments').value,
            start_date: document.getElementById('projectTaskStartDate').value,
            end_date: document.getElementById('projectTaskEndDate').value,
            parent_id: parentId || null
        };

        if (taskId) {
            // Edit existing task
            data.status = document.getElementById('projectTaskStatus').value;
            const res = await fetch(`/api/projects/${projectId}/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await res.json();
            if (res.ok) {
                closeProjectTaskModal();
                window.location.reload();
            } else {
                alert(result.error || 'Failed to update task');
            }
        } else {
            // Create new task
            const res = await fetch(`/api/projects/${projectId}/tasks`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (res.ok) {
                closeProjectTaskModal();
                window.location.reload();
            } else {
                const result = await res.json();
                alert(result.error || 'Failed to create task');
            }
        }
    });

    // Handle project deletion
    document.addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-btn') || e.target.closest('.delete-btn')) {
            const btn = e.target.classList.contains('delete-btn') ? e.target : e.target.closest('.delete-btn');
            const itemType = btn.getAttribute('data-type');
            const itemId = btn.getAttribute('data-id');
            const projectId = btn.getAttribute('data-project-id');
            const taskId = btn.getAttribute('data-task-id');

            if (itemType === 'projects' && itemId) {
                if (!confirm('Are you sure you want to delete this project?')) return;

                const res = await fetch(`/api/projects/${itemId}`, { method: 'DELETE' });
                if (res.ok) {
                    window.location.reload();
                } else {
                    alert('Failed to delete project');
                }
            } else if (itemType === 'project-tasks' && projectId && taskId) {
                if (!confirm('Are you sure you want to delete this task?')) return;

                const res = await fetch(`/api/projects/${projectId}/tasks/${taskId}`, { method: 'DELETE' });
                if (res.ok) {
                    window.location.reload();
                } else {
                    alert('Failed to delete task');
                }
            }
        }

        // Handle project edit button
        if (e.target.classList.contains('edit-btn') || e.target.closest('.edit-btn')) {
            const btn = e.target.classList.contains('edit-btn') ? e.target : e.target.closest('.edit-btn');
            const editType = btn.getAttribute('data-edit-type');

            if (editType === 'project') {
                const id = btn.getAttribute('data-edit-id');
                const name = btn.getAttribute('data-edit-name');
                const description = btn.getAttribute('data-edit-description');
                const startDate = btn.getAttribute('data-edit-start-date');
                const endDate = btn.getAttribute('data-edit-end-date');
                const status = btn.getAttribute('data-edit-status');

                openEditProjectModal(id, name, description, startDate, endDate, status);
            }
        }
    });

    // Close modals on outside click - extend existing onclick handler
    const existingOnClick = window.onclick;
    window.onclick = function (event) {
        if (existingOnClick) existingOnClick(event);
        if (event.target == modal) modal.style.display = "none";
        if (event.target == editModal) editModal.style.display = "none";
        if (event.target == commentsModal) commentsModal.style.display = "none";
        if (event.target == kbModal) kbModal.style.display = "none";
        if (event.target == kbResultModal) kbResultModal.style.display = "none";
        if (projectModal && event.target == projectModal) projectModal.style.display = "none";
        if (projectTaskModal && event.target == projectTaskModal) projectTaskModal.style.display = "none";
        if (projectTaskCommentsModal && event.target == projectTaskCommentsModal) projectTaskCommentsModal.style.display = "none";
    }
    window.copyToClipboard = function (text) {
        if (!text) return;

        // Try modern clipboard API first
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                showCopyFeedback();
            }).catch(err => {
                console.error('Clipboard write failed:', err);
                fallbackCopy(text);
            });
        } else {
            fallbackCopy(text);
        }
    }

    function fallbackCopy(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed'; // Avoid scrolling to bottom
        textArea.style.left = '-9999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            const successful = document.execCommand('copy');
            if (successful) showCopyFeedback();
        } catch (err) {
            console.error('Fallback copy failed:', err);
            alert('Failed to copy. Please copy manually.');
        }

        document.body.removeChild(textArea);
    }

    function showCopyFeedback() {
        const el = document.createElement('div');
        el.innerText = "Copied!";
        el.style.position = 'fixed';
        el.style.bottom = '20px';
        el.style.left = '50%';
        el.style.transform = 'translateX(-50%)';
        el.style.background = 'rgba(0,0,0,0.8)';
        el.style.color = 'white';
        el.style.padding = '10px 20px';
        el.style.borderRadius = '20px'; // More rounded
        el.style.zIndex = '9999';
        el.style.fontSize = '0.9rem';
        el.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
        el.style.animation = 'fadeIn 0.3s ease-out';

        document.body.appendChild(el);
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transition = 'opacity 0.3s ease';
            setTimeout(() => document.body.removeChild(el), 300);
        }, 1500);
    }
});

// --- Drag and Drop Logic ---
document.addEventListener('DOMContentLoaded', () => {
    restoreDashboardOrder();
    enableDragAndDrop();
});

function restoreDashboardOrder() {
    // Restore Section Order
    const dashboardGrid = document.querySelector('.dashboard-grid');
    if (dashboardGrid) {
        const savedSectionOrder = localStorage.getItem('dashboardSectionOrder');
        if (savedSectionOrder) {
            try {
                const order = JSON.parse(savedSectionOrder);
                const currentSections = Array.from(dashboardGrid.querySelectorAll('.section-container'));
                const sectionMap = new Map();
                currentSections.forEach(s => sectionMap.set(s.getAttribute('data-section'), s));

                // Clear grid and re-append in order
                // But only if all sections are present to avoid data loss on partial loads?
                // Or just append efficiently.

                order.forEach(sectionName => {
                    const section = sectionMap.get(sectionName);
                    if (section) {
                        dashboardGrid.appendChild(section);
                    }
                });
                // Append any remaining (new) sections not in saved order
                currentSections.forEach(s => {
                    if (!order.includes(s.getAttribute('data-section'))) {
                        dashboardGrid.appendChild(s);
                    }
                });
            } catch (e) {
                console.error("Error restoring section order", e);
            }
        }
    }

    // Restore Items Order (Tasks, Reminders, Projects)
    const lists = [
        { selector: '.task-list', key: 'dashboardtasksOrder', type: 'task' },
        { selector: '.reminder-list', key: 'dashboardremindersOrder', type: 'reminder' },
        { selector: '.project-list', key: 'dashboardprojectsOrder', type: 'project' }
    ];

    lists.forEach(listInfo => {
        const listContainer = document.querySelector(listInfo.selector);
        if (listContainer) {
            const savedOrder = localStorage.getItem(listInfo.key);
            if (savedOrder) {
                try {
                    const order = JSON.parse(savedOrder);
                    const currentItems = Array.from(listContainer.querySelectorAll('.item-card'));
                    const itemMap = new Map();
                    currentItems.forEach(item => itemMap.set(item.getAttribute('data-item-id'), item));

                    order.forEach(itemId => {
                        const item = itemMap.get(String(itemId));
                        if (item) {
                            listContainer.appendChild(item);
                        }
                    });

                    // Append remaining
                    currentItems.forEach(item => {
                        if (!order.includes(item.getAttribute('data-item-id'))) {
                            listContainer.appendChild(item);
                        }
                    });
                } catch (e) {
                    console.error(`Error restoring ${listInfo.type} order`, e);
                }
            }
        }
    });
}

function enableDragAndDrop() {
    // Section Dragging
    const sections = document.querySelectorAll('.section-container');
    const dashboardGrid = document.querySelector('.dashboard-grid');

    if (dashboardGrid) {
        sections.forEach(section => {
            section.setAttribute('draggable', 'true');
            section.addEventListener('dragstart', handleSectionDragStart);
            section.addEventListener('dragover', handleSectionDragOver);
            section.addEventListener('drop', handleSectionDrop);
            section.addEventListener('dragenter', handleSectionDragEnter);
            section.addEventListener('dragleave', handleSectionDragLeave);
        });
    }

    // Item Dragging (Tasks, Reminders, Projects)
    const itemLists = document.querySelectorAll('.task-list, .reminder-list, .project-list');

    itemLists.forEach(list => {
        list.addEventListener('dragstart', handleItemDragStart);
        list.addEventListener('dragover', handleItemDragOver);
        list.addEventListener('drop', handleItemDrop);
    });
}

// Global variable to store dragged element
let draggedElement = null;
let draggedType = null; // 'section' or 'item'

// Section Handlers
function handleSectionDragStart(e) {
    draggedElement = this;
    draggedType = 'section';
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
    this.style.opacity = '0.4';
}

function handleSectionDragOver(e) {
    if (draggedType !== 'section') return;
    if (e.preventDefault) e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleSectionDragEnter(e) {
    if (draggedType !== 'section') return;
    this.classList.add('over');
}

function handleSectionDragLeave(e) {
    if (draggedType !== 'section') return;
    this.classList.remove('over');
}

function handleSectionDrop(e) {
    if (e.stopPropagation) e.stopPropagation();
    if (draggedType !== 'section') return false;

    if (draggedElement !== this) {
        // Swap or Move logic
        // We need to reorder in the DOM.
        // A simple way is to swap the elements or insertBefore/After
        const grid = this.parentNode;

        // Find positions
        const allSections = Array.from(grid.querySelectorAll('.section-container'));
        const draggedIndex = allSections.indexOf(draggedElement);
        const targetIndex = allSections.indexOf(this);

        if (draggedIndex < targetIndex) {
            grid.insertBefore(draggedElement, this.nextSibling);
        } else {
            grid.insertBefore(draggedElement, this);
        }

        // Save Order
        const newOrder = Array.from(grid.querySelectorAll('.section-container')).map(s => s.getAttribute('data-section'));
        localStorage.setItem('dashboardSectionOrder', JSON.stringify(newOrder));
    }

    this.classList.remove('over');
    draggedElement.style.opacity = '1';
    draggedElement = null;
    draggedType = null;
    return false;
}

// Item Handlers
function handleItemDragStart(e) {
    e.stopPropagation(); // Prevent section drag start
    // Ensure we are dragging an item card
    let target = e.target;
    if (!target.classList.contains('item-card')) {
        target = target.closest('.item-card');
    }
    if (!target) return;

    draggedElement = target;
    draggedType = 'item';
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', target.getAttribute('data-item-id'));
    target.style.opacity = '0.4';
}

function handleItemDragOver(e) {
    if (draggedType !== 'item') return;
    e.preventDefault();
    e.stopPropagation();
    // Verify we are over the same list type
    const list = e.target.closest('.task-list, .reminder-list, .project-list');
    // Check if dragging onto same container
    if (list && draggedElement.parentNode === list) {
        e.dataTransfer.dropEffect = 'move';
    } else {
        e.dataTransfer.dropEffect = 'none';
    }
    return false;
}

function handleItemDrop(e) {
    e.stopPropagation();
    if (draggedType !== 'item') return false;

    const targetCard = e.target.closest('.item-card');
    const targetList = e.target.closest('.task-list, .reminder-list, .project-list');

    if (targetList && draggedElement.parentNode === targetList) {
        if (targetCard && targetCard !== draggedElement) {
            // Determine insert position (before or after)
            const rect = targetCard.getBoundingClientRect();
            const relX = e.clientX - rect.left;
            // Depending on layout (grid vs list). Dashboard uses grid.
            // Simplified: Insert before

            // Just swap for simplicity or insertBefore
            const children = Array.from(targetList.children);
            const draggedIdx = children.indexOf(draggedElement);
            const targetIdx = children.indexOf(targetCard);

            if (draggedIdx < targetIdx) {
                targetList.insertBefore(draggedElement, targetCard.nextSibling);
            } else {
                targetList.insertBefore(draggedElement, targetCard);
            }
        } else if (!targetCard && targetList) {
            // Dropped on empty space in list
            targetList.appendChild(draggedElement);
        }

        // Save Order
        const itemType = draggedElement.getAttribute('data-item-type'); // 'task', 'reminder', 'project'
        const container = draggedElement.parentNode;
        const itemOrder = Array.from(container.querySelectorAll(`[data-item-type="${itemType}"]`)).map(item => item.getAttribute('data-item-id'));
        if (itemType) {
            localStorage.setItem(`dashboard${itemType}sOrder`, JSON.stringify(itemOrder));
        }
    }

    draggedElement.style.opacity = '1';
    draggedElement = null;
    draggedType = null;
    return false;
}
