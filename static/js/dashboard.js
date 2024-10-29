document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }
    loadUserProfile();
    setupChatInterface();
});

function loadUserProfile() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    fetch('/learning_report', {
        headers: {
            'Authorization': token
        }
    })
    .then(response => {
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/';
            throw new Error('Unauthorized');
        }
        return response.json();
    })
    .then(data => {
        // Update email and learning difficulty
        const userEmail = document.getElementById('userEmail');
        if (userEmail) userEmail.textContent = data.email || 'Usuario';

        // Update profile summary
        const learningStyle = document.getElementById('learningStyle');
        if (learningStyle) {
            let styleText = data.learning_style || 'No definido';
            if (data.learning_difficulty && data.learning_difficulty !== 'Ninguno') {
                styleText += ` (${data.learning_difficulty})`;
            }
            learningStyle.textContent = styleText;
        }

        // Update progress bar
        const progressBar = document.getElementById('profileProgress');
        if (progressBar) {
            progressBar.style.width = `${data.progress || 0}%`;
            progressBar.textContent = `${data.progress || 0}%`;
        }

        // Update statistics
        document.querySelector('[data-stat="time"]').textContent = `${data.total_time}h`;
        document.querySelector('[data-stat="sessions"]').textContent = data.session_count;
        document.querySelector('[data-stat="streak"]').textContent = `${data.streak} días`;
        document.querySelector('[data-stat="last-session"]').textContent = data.last_session || 'Sin actividad';
    })
    .catch(error => {
        if (error.message !== 'Unauthorized') {
            console.error('Error loading learning report:', error);
            showError('Error al cargar el reporte de aprendizaje');
        }
    });
}

function setupChatInterface() {
    const chatForm = document.getElementById('chatForm');
    const chatMessages = document.getElementById('chatMessages');
    const messageInput = document.getElementById('messageInput');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const removeFile = document.getElementById('removeFile');
    let currentFile = null;

    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                currentFile = e.target.files[0];
                fileName.textContent = currentFile.name;
                filePreview.style.display = 'block';
            }
        });
    }

    if (removeFile) {
        removeFile.addEventListener('click', function() {
            currentFile = null;
            if (fileInput) fileInput.value = '';
            filePreview.style.display = 'none';
        });
    }

    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const token = localStorage.getItem('token');
            if (!token) {
                window.location.href = '/';
                return;
            }

            const message = messageInput.value.trim();
            if (!message && !currentFile) {
                showError('Por favor, escribe un mensaje o adjunta un archivo.');
                return;
            }

            const formData = new FormData();
            formData.append('message', message);
            if (currentFile) {
                formData.append('file', currentFile);
            }

            // Show loading state
            const sendButton = document.getElementById('sendButton');
            if (!sendButton) return;
            
            const originalText = sendButton.textContent;
            sendButton.disabled = true;
            sendButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Enviando...';

            // Add user message to chat
            if (message) {
                appendMessage('user', message);
            }
            if (currentFile) {
                appendMessage('user', `[Archivo adjunto: ${currentFile.name}]`);
            }

            messageInput.value = '';

            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Authorization': token
                },
                body: formData
            })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                appendMessage('ai', data.response, data.chat_id);
            })
            .catch(error => {
                console.error('Error:', error);
                showError('Error al enviar mensaje: ' + error.message);
            })
            .finally(() => {
                // Reset button state
                sendButton.disabled = false;
                sendButton.textContent = originalText;
                // Reset file input
                currentFile = null;
                if (fileInput) fileInput.value = '';
                filePreview.style.display = 'none';
            });
        });
    }
}

function submitFeedback(chatId, helpful, button) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    // Disable both thumbs buttons
    const btnGroup = button.closest('.btn-group');
    const buttons = btnGroup.querySelectorAll('button');
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.classList.remove('btn-outline-success', 'btn-outline-danger');
        btn.classList.add(btn === button ? (helpful ? 'btn-success' : 'btn-danger') : 'btn-secondary');
    });

    // Show feedback message
    const feedbackStatus = button.closest('.feedback-buttons').querySelector('.feedback-status');
    if (feedbackStatus) {
        feedbackStatus.textContent = '¡Gracias por tu valoración!';
        feedbackStatus.classList.remove('d-none');
        feedbackStatus.style.color = helpful ? '#198754' : '#dc3545';
    }

    fetch('/chat_feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token
        },
        body: JSON.stringify({
            chat_id: chatId,
            helpful: helpful
        })
    })
    .catch(error => console.error('Error submitting feedback:', error));
}

function submitUnderstanding(chatId, level, button) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }

    // Disable all rating buttons
    const btnGroup = button.closest('.btn-group');
    const buttons = btnGroup.querySelectorAll('button');
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.classList.remove('btn-outline-primary');
        btn.classList.add(btn === button ? 'btn-primary' : 'btn-secondary');
    });

    // Show feedback message
    const feedbackStatus = button.closest('.feedback-buttons').querySelector('.feedback-status');
    if (feedbackStatus) {
        feedbackStatus.textContent = '¡Gracias por indicar tu nivel de comprensión!';
        feedbackStatus.classList.remove('d-none');
        feedbackStatus.style.color = '#0d6efd';
    }

    fetch('/chat_feedback', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token
        },
        body: JSON.stringify({
            chat_id: chatId,
            understanding: level
        })
    })
    .catch(error => console.error('Error submitting understanding level:', error));
}

function appendMessage(type, content, chatId = null) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    messageDiv.textContent = content;

    if (type === 'ai') {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-buttons mt-2';
        feedbackDiv.innerHTML = `
            <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-success" onclick="submitFeedback(${chatId}, true, this)">
                    <i class="bi bi-hand-thumbs-up"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="submitFeedback(${chatId}, false, this)">
                    <i class="bi bi-hand-thumbs-down"></i>
                </button>
            </div>
            <div class="understanding-buttons mt-2">
                <small class="text-muted">¿Qué tan bien entendiste esto?</small>
                <div class="btn-group" role="group">
                    ${[1,2,3,4,5].map(n => 
                        `<button class="btn btn-sm btn-outline-primary" onclick="submitUnderstanding(${chatId}, ${n}, this)">${n}</button>`
                    ).join('')}
                </div>
            </div>
            <div class="feedback-status mt-2 text-success d-none"></div>
        `;
        messageDiv.appendChild(feedbackDiv);
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function toggleChat(show) {
    const chatSection = document.getElementById('chatSection');
    if (chatSection) {
        chatSection.style.display = show ? 'block' : 'none';
        if (show) {
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }
}

function showError(message) {
    const errorToast = document.getElementById('errorToast');
    if (errorToast) {
        const errorBody = errorToast.querySelector('.toast-body');
        errorBody.textContent = message;
        const toast = new bootstrap.Toast(errorToast);
        toast.show();
    } else {
        console.error(message);
    }
}
