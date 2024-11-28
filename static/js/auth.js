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
});

async function handleResponse(response) {
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error del servidor');
        }
        return data;
    } else {
        const text = await response.text();
        if (!response.ok) {
            throw new Error(text || 'Error del servidor');
        }
        return { message: text };
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
            tokenDisplay.textContent = 'Tu token: ' + data.token;
            tokenDisplay.style.display = 'block';
            // Save user data in localStorage
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify({
                email: data.email,
                token: data.token,
                questionnaire_completed: false
            }));
            
            // Add a small delay before redirecting
            setTimeout(() => {
                window.location.href = '/questionnaire';
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
            // Update user data in localStorage
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            user.token = cleanToken;
            user.email = data.email;
            localStorage.setItem('user', JSON.stringify(user));
            localStorage.setItem('token', cleanToken);
            
            // Check questionnaire completion from localStorage
            const questionnaire = localStorage.getItem('questionnaire');
            window.location.href = questionnaire ? '/dashboard' : '/questionnaire';
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error al iniciar sesión: ' + error.message);
    }
}
