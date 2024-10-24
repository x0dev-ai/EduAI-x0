document.addEventListener('DOMContentLoaded', function() {
    loadUserProfile();
    setupChatInterface();
});

function loadUserProfile() {
    fetch('/learning_report', {
        headers: {
            'Authorization': localStorage.getItem('token')
        }
    })
    .then(response => response.json())
    .then(data => {
        // Update profile progress
        const progressBar = document.getElementById('profileProgress');
        progressBar.style.width = `${data.progress || 0}%`;
        progressBar.textContent = `${data.progress || 0}%`;

        // Update learning style
        const learningStyle = document.getElementById('learningStyle');
        learningStyle.textContent = data.learning_style || 'No definido';

        // Update recommendations
        const recommendationsList = document.getElementById('recommendationsList');
        const recommendations = [
            'Crea un horario de estudio detallado y síguelo consistentemente',
            'Utiliza guías paso a paso y materiales bien organizados',
            'Establece objetivos claros y medibles para cada sesión',
            'Usa listas de verificación para seguir tu progreso'
        ];
        recommendationsList.innerHTML = recommendations.map(rec => 
            `<li class="mb-2"><i class="bi bi-check2-circle text-success me-2"></i>${rec}</li>`
        ).join('');

        // Update schedule
        const scheduleList = document.getElementById('scheduleList');
        const schedule = [
            { time: 'Mañana (8:00 - 9:30)', activity: 'Estudio enfocado en nuevos conceptos' },
            { time: 'Tarde (15:00 - 16:00)', activity: 'Repaso y ejercicios prácticos' },
            { time: 'Noche (19:00 - 20:00)', activity: 'Organización y planificación' }
        ];
        scheduleList.innerHTML = schedule.map(slot => `
            <div class="mb-2">
                <strong>${slot.time}:</strong>
                <span class="text-muted">${slot.activity}</span>
            </div>
        `).join('');

        // Update progress
        document.getElementById('completedQuestions').textContent = data.completed_questions || '0';

        // Update progress details
        const progressDetails = document.getElementById('progressDetails');
        if (data.mastery_scores) {
            const details = Object.entries(data.mastery_scores).map(([topic, score]) => `
                <div class="mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <span>${topic}</span>
                        <span class="badge bg-info">${Math.round(score * 100)}%</span>
                    </div>
                    <div class="progress" style="height: 5px;">
                        <div class="progress-bar" role="progressbar" style="width: ${score * 100}%"></div>
                    </div>
                </div>
            `).join('');
            progressDetails.innerHTML = details;
        }
    })
    .catch(error => {
        console.error('Error loading learning report:', error);
        showError('Error al cargar el reporte de aprendizaje');
    });
}

function setupChatInterface() {
    const chatForm = document.getElementById('chatForm');
    const chatMessages = document.getElementById('chatMessages');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const fileInput = document.getElementById('fileInput');
    const filePreview = document.getElementById('filePreview');
    const fileName = document.getElementById('fileName');
    const removeFile = document.getElementById('removeFile');
    let currentFile = null;
    let lastChatId = null;

    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            currentFile = e.target.files[0];
            fileName.textContent = currentFile.name;
            filePreview.style.display = 'block';
        }
    });

    removeFile.addEventListener('click', function() {
        currentFile = null;
        fileInput.value = '';
        filePreview.style.display = 'none';
    });

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (message || currentFile) {
            sendMessage(message);
            messageInput.value = '';
        }
    });

    function createFeedbackButtons(chatId) {
        const feedbackDiv = document.createElement('div');
        feedbackDiv.classList.add('feedback-buttons', 'mt-2', 'mb-3');
        
        const helpfulBtn = document.createElement('button');
        helpfulBtn.classList.add('btn', 'btn-sm', 'btn-outline-success', 'me-2');
        helpfulBtn.innerHTML = '👍 Útil';
        helpfulBtn.onclick = () => submitFeedback(chatId, true);
        
        const notHelpfulBtn = document.createElement('button');
        notHelpfulBtn.classList.add('btn', 'btn-sm', 'btn-outline-danger', 'me-2');
        notHelpfulBtn.innerHTML = '👎 No útil';
        notHelpfulBtn.onclick = () => submitFeedback(chatId, false);
        
        const understandingDiv = document.createElement('div');
        understandingDiv.classList.add('mt-2');
        understandingDiv.innerHTML = '<small class="text-muted">¿Qué tan bien entendiste la respuesta?</small><br>';
        
        for (let i = 1; i <= 5; i++) {
            const levelBtn = document.createElement('button');
            levelBtn.classList.add('btn', 'btn-sm', 'btn-outline-secondary', 'me-1');
            levelBtn.textContent = i;
            levelBtn.onclick = () => submitUnderstanding(chatId, i);
            understandingDiv.appendChild(levelBtn);
        }
        
        feedbackDiv.appendChild(helpfulBtn);
        feedbackDiv.appendChild(notHelpfulBtn);
        feedbackDiv.appendChild(understandingDiv);
        
        return feedbackDiv;
    }

    function submitFeedback(chatId, helpful) {
        fetch('/chat_feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': localStorage.getItem('token')
            },
            body: JSON.stringify({
                chat_id: chatId,
                helpful: helpful
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            showSuccess('¡Gracias por tu feedback!');
            loadUserProfile(); // Reload profile to update progress
        })
        .catch(error => {
            showError('Error al enviar feedback: ' + error.message);
        });
    }

    function submitUnderstanding(chatId, level) {
        fetch('/chat_feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': localStorage.getItem('token')
            },
            body: JSON.stringify({
                chat_id: chatId,
                understanding: level
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            showSuccess('¡Gracias por indicar tu nivel de comprensión!');
            loadUserProfile(); // Reload profile to update progress
        })
        .catch(error => {
            showError('Error al enviar nivel de comprensión: ' + error.message);
        });
    }

    function sendMessage(message) {
        messageInput.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Enviando...';

        displayMessage(message, 'user-message');

        const formData = new FormData();
        if (message) formData.append('message', message);
        if (currentFile) formData.append('file', currentFile);

        fetch('/chat', {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('token')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            displayMessage(data.response, 'ai-message');
            lastChatId = data.chat_id;
            
            if (lastChatId) {
                const feedbackButtons = createFeedbackButtons(lastChatId);
                chatMessages.appendChild(feedbackButtons);
            }

            // Update user profile after each interaction
            loadUserProfile();
        })
        .catch((error) => {
            showError('Error: ' + error.message);
            displayMessage('Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta nuevamente.', 'error-message');
        })
        .finally(() => {
            messageInput.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = 'Enviar';
            messageInput.focus();
            currentFile = null;
            fileInput.value = '';
            filePreview.style.display = 'none';
        });
    }

    function displayMessage(message, className) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', className, 'mb-2', 'p-2');
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function showError(message) {
    const errorToast = document.getElementById('errorToast');
    const errorBody = errorToast.querySelector('.toast-body');
    errorBody.textContent = message;
    const toast = new bootstrap.Toast(errorToast);
    toast.show();
}

function showSuccess(message) {
    const successToast = document.getElementById('successToast');
    if (!successToast) {
        const toastContainer = document.querySelector('.toast-container');
        const successToastHTML = `
            <div id="successToast" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header bg-success text-white">
                    <strong class="me-auto">Éxito</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Cerrar"></button>
                </div>
                <div class="toast-body"></div>
            </div>
        `;
        toastContainer.insertAdjacentHTML('beforeend', successToastHTML);
    }
    
    const successToastElement = document.getElementById('successToast');
    const successBody = successToastElement.querySelector('.toast-body');
    successBody.textContent = message;
    const toast = new bootstrap.Toast(successToastElement);
    toast.show();
}
