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
            // Clear invalid token and redirect to login
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
        updateStatistics(data);
    })
    .catch(error => {
        if (error.message !== 'Unauthorized') {
            console.error('Error loading learning report:', error);
            showError('Error al cargar el reporte de aprendizaje');
        }
    });
}

function updateStatistics(data) {
    // Update session count
    const sessionCount = document.querySelector('.col-md-3:nth-child(2) .fs-3');
    if (sessionCount) {
        sessionCount.textContent = data.completed_questions || '0';
    }

    // Update study time (if available)
    const studyTime = document.querySelector('.col-md-3:nth-child(1) .fs-3');
    if (studyTime && data.total_study_time) {
        const hours = Math.floor(data.total_study_time / 3600);
        studyTime.textContent = `${hours}h`;
    }

    // Update streak (if available)
    const streak = document.querySelector('.col-md-3:nth-child(3) .fs-3');
    if (streak && data.current_streak) {
        streak.textContent = `${data.current_streak} días`;
    }

    // Update last session
    const lastSession = document.querySelector('.col-md-3:nth-child(4) .text-muted');
    if (lastSession && data.last_session) {
        const date = new Date(data.last_session);
        lastSession.textContent = date.toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

function toggleChat(show) {
    const chatSection = document.getElementById('chatSection');
    if (chatSection) {
        chatSection.style.display = show ? 'block' : 'none';
        if (show) {
            chatSection.scrollIntoView({ behavior: 'smooth' });
            document.getElementById('messageInput')?.focus();
        }
    }
}

function setupChatInterface() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }

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
            fileInput.value = '';
            filePreview.style.display = 'none';
        });
    }

    if (chatForm) {
        chatForm.addEventListener('submit', function(e) {
            e.preventDefault();
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
                if (response.status === 401) {
                    localStorage.removeItem('token');
                    window.location.href = '/';
                    throw new Error('Unauthorized');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                appendMessage('ai', data.response, data.chat_id);
            })
            .catch(error => {
                if (error.message !== 'Unauthorized') {
                    console.error('Error:', error);
                    showError('Error al enviar mensaje: ' + error.message);
                }
            })
            .finally(() => {
                // Reset button state
                sendButton.disabled = false;
                sendButton.textContent = originalText;
                // Reset file input
                currentFile = null;
                fileInput.value = '';
                filePreview.style.display = 'none';
            });
        });
    }
}

function appendMessage(type, content, chatId = null) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}-message`;
    messageDiv.textContent = content;

    if (type === 'ai') {
        // Add feedback buttons for AI messages
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'feedback-buttons mt-2';
        feedbackDiv.innerHTML = `
            <div class="btn-group" role="group">
                <button class="btn btn-sm btn-outline-success" onclick="submitFeedback(${chatId}, true)">
                    <i class="bi bi-hand-thumbs-up"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="submitFeedback(${chatId}, false)">
                    <i class="bi bi-hand-thumbs-down"></i>
                </button>
            </div>
            <div class="understanding-buttons mt-2">
                <small class="text-muted">¿Qué tan bien entendiste esto?</small>
                <div class="btn-group" role="group">
                    ${[1,2,3,4,5].map(n => 
                        `<button class="btn btn-sm btn-outline-primary" onclick="submitUnderstanding(${chatId}, ${n})">${n}</button>`
                    ).join('')}
                </div>
            </div>
        `;
        messageDiv.appendChild(feedbackDiv);
    }

    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function submitFeedback(chatId, helpful) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
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
    .then(response => {
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/';
            throw new Error('Unauthorized');
        }
        return response.json();
    })
    .catch(error => {
        if (error.message !== 'Unauthorized') {
            console.error('Error submitting feedback:', error);
        }
    });
}

function submitUnderstanding(chatId, level) {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
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
    .then(response => {
        if (response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/';
            throw new Error('Unauthorized');
        }
        return response.json();
    })
    .catch(error => {
        if (error.message !== 'Unauthorized') {
            console.error('Error submitting understanding level:', error);
        }
    });
}

function showError(message) {
    const errorToast = document.getElementById('errorToast');
    const errorBody = errorToast.querySelector('.toast-body');
    errorBody.textContent = message;
    const toast = new bootstrap.Toast(errorToast);
    toast.show();
}
