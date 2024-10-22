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
        // Populate other profile information as needed
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}

function setupChatInterface() {
    const chatForm = document.getElementById('chatForm');
    const chatMessages = document.getElementById('chatMessages');

    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        if (message) {
            sendMessage(message);
            messageInput.value = '';
        }
    });

    function sendMessage(message) {
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
            displayMessage(data.response, 'ai-message');
        })
        .catch((error) => {
            console.error('Error:', error);
            displayMessage('Sorry, there was an error processing your request.', 'ai-message');
        });
    }

    function displayMessage(message, className) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', className);
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}
