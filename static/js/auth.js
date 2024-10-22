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

function getToken(email) {
    fetch('/get_token', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.token) {
            alert('Your token: ' + data.token);
            localStorage.setItem('token', data.token);
            window.location.href = '/questionnaire';
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}

function login(token) {
    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token: token }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.message === 'Login successful') {
            localStorage.setItem('token', token);
            if (data.questionnaire_completed) {
                window.location.href = '/dashboard';
            } else {
                window.location.href = '/questionnaire';
            }
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}
