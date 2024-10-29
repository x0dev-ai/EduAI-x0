document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/';
        return;
    }
    loadUserProfile();
    setupChatInterface();
});

// ... [previous functions remain unchanged until submitFeedback] ...

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

// ... [rest of the file remains unchanged] ...
