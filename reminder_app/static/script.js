document.addEventListener('DOMContentLoaded', () => {
    // Theme Logic
    window.setTheme = function (theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        const radio = document.getElementById(theme + 'Theme');
        const radioS = document.getElementById(theme + 'Themes');
        if (radio) radio.checked = true;
        if (radioS) radioS.checked = true;
    }

    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

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
        window.openEditModal = function() {};
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
});

