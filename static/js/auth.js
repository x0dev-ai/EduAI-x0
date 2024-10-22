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
            alert('Tu token: ' + data.token);
            localStorage.setItem('token', data.token);
            window.location.href = '/questionnaire';
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error al obtener el token: ' + error.message);
    }
}

async function login(token) {
    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token: token }),
        });

        const data = await handleResponse(response);
        
        if (data.message === 'Login successful') {
            localStorage.setItem('token', token);
            window.location.href = data.questionnaire_completed ? '/dashboard' : '/questionnaire';
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Error al iniciar sesión: ' + error.message);
    }
}
