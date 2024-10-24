document.addEventListener('DOMContentLoaded', function() {
    const tokenForm = document.getElementById('tokenForm');
    const loginForm = document.getElementById('loginForm');

    if (tokenForm) {
        tokenForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = document.getElementById('email').value;
            getToken(email);
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const token = document.getElementById('token').value;
            login(token);
        });
    }

    // Check if we need to restore any previous questionnaire state
    const savedQuestionnaireState = sessionStorage.getItem('questionnaireState');
    if (savedQuestionnaireState && window.location.pathname === '/questionnaire') {
        try {
            const state = JSON.parse(savedQuestionnaireState);
            restoreQuestionnaireState(state);
        } catch (error) {
            console.error('Error restoring questionnaire state:', error);
            sessionStorage.removeItem('questionnaireState');
        }
    }
});

function handleResponse(response) {
    if (!response.ok) {
        return response.json().then(data => {
            throw new Error(data.error || 'Error del servidor');
        });
    }
    return response.json();
}

function showError(message) {
    const errorToast = document.getElementById('errorToast');
    if (errorToast) {
        const errorBody = errorToast.querySelector('.toast-body');
        errorBody.textContent = message;
        const toast = new bootstrap.Toast(errorToast);
        toast.show();
    } else {
        alert(message);
    }
}

async function getToken(email) {
    try {
        const response = await fetch('/get_token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email }),
        });

        const data = await handleResponse(response);
        
        if (data.token) {
            const tokenDisplay = document.getElementById('tokenDisplay');
            tokenDisplay.textContent = `Token para ${email}: ${data.token}`;
            tokenDisplay.style.display = 'block';
            localStorage.setItem('token', data.token);
            
            // Clear any existing questionnaire state
            sessionStorage.removeItem('questionnaireState');
            
            // Add a small delay before redirecting
            setTimeout(() => {
                window.location.href = data.redirect || '/questionnaire';
            }, 3000);
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error al obtener el token: ' + error.message);
    }
}

async function login(token) {
    try {
        // Clean the token before sending
        const cleanToken = token.trim().replace(/\s+/g, '');
        
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: cleanToken }),
        });

        const data = await handleResponse(response);
        
        if (data.message === 'Login successful') {
            localStorage.setItem('token', cleanToken);
            
            // Clear questionnaire state if going to dashboard
            if (data.redirect === '/dashboard') {
                sessionStorage.removeItem('questionnaireState');
            }
            
            window.location.href = data.redirect;
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error al iniciar sesión: ' + error.message);
    }
}

function saveQuestionnaireState(state) {
    sessionStorage.setItem('questionnaireState', JSON.stringify(state));
}

function restoreQuestionnaireState(state) {
    const form = document.getElementById('questionnaireForm');
    if (!form) return;

    // Restore form values
    Object.entries(state).forEach(([name, value]) => {
        const input = form.querySelector(`[name="${name}"]`);
        if (input) {
            if (input.type === 'radio') {
                const radio = form.querySelector(`[name="${name}"][value="${value}"]`);
                if (radio) radio.checked = true;
            } else {
                input.value = value;
            }
        }
    });
}
