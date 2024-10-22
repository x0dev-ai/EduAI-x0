document.addEventListener('DOMContentLoaded', function() {
    loadUserProfile();
    setupChatInterface();
});

function loadUserProfile() {
    fetch('/get_user_profile', {
        method: 'GET',
        headers: {
            'Authorization': localStorage.getItem('token')
        }
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('userEmail').textContent = data.email;
        document.getElementById('userType').textContent = data.user_type;
        
        // Add user type description
        const typeDescriptions = {
            'A': 'Recibirás explicaciones detalladas y desafiantes para maximizar tu aprendizaje.',
            'B': 'Recibirás explicaciones balanceadas con ejemplos prácticos.',
            'C': 'Recibirás explicaciones claras y paso a paso con ejemplos cotidianos.'
        };
        const description = document.getElementById('userTypeDescription');
        description.innerHTML = `<p class="mt-2"><small class="text-muted">${typeDescriptions[data.user_type] || ''}</small></p>`;
    })
    .catch((error) => {
        showError('Error al cargar el perfil: ' + error.message);
    });
}

function setupChatInterface() {
    const chatForm = document.getElementById('chatForm');
    const chatMessages = document.getElementById('chatMessages');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (message) {
            sendMessage(message);
            messageInput.value = '';
        }
    });

    function sendMessage(message) {
        // Disable input while processing
        messageInput.disabled = true;
        sendButton.disabled = true;
        sendButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Enviando...';

        // Display user message
        displayMessage(message, 'user-message');

        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': localStorage.getItem('token')
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            displayMessage(data.response, 'ai-message');
        })
        .catch((error) => {
            showError('Error: ' + error.message);
            displayMessage('Lo siento, hubo un error al procesar tu mensaje. Por favor, intenta nuevamente.', 'error-message');
        })
        .finally(() => {
            // Re-enable input
            messageInput.disabled = false;
            sendButton.disabled = false;
            sendButton.innerHTML = 'Enviar';
            messageInput.focus();
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
