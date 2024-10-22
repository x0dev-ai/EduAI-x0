document.addEventListener('DOMContentLoaded', function() {
    const questionnaireForm = document.getElementById('questionnaireForm');
    
    if (questionnaireForm) {
        questionnaireForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitQuestionnaire();
        });
    }
});

function submitQuestionnaire() {
    const formData = {
        question1: document.querySelector('input[name="question1"]:checked').value,
        question2: document.querySelector('input[name="question2"]:checked').value,
        question3: document.querySelector('input[name="question3"]:checked').value,
        question4: parseInt(document.getElementById('question4').value),
        question5: document.getElementById('question5').value,
        question6: Array.from(document.querySelectorAll('input[name="question6"]:checked')).map(el => el.value)
    };

    // Get token from localStorage
    const token = localStorage.getItem('token');
    if (!token) {
        alert('No se encontró el token de autorización. Por favor, inicie sesión nuevamente.');
        window.location.href = '/';
        return;
    }

    fetch('/submit_questionnaire', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token  // Add the Authorization header
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Error en la respuesta del servidor: ' + response.status);
        }
        return response.json();
    })
    .then(data => {
        if (data.user_type) {
            alert('Cuestionario enviado exitosamente. Tu tipo de usuario es: ' + data.user_type);
            window.location.href = '/dashboard';
        } else {
            throw new Error(data.message || 'Error desconocido');
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        alert('Error al enviar el cuestionario: ' + error.message);
        if (error.message.includes('401')) {
            window.location.href = '/';  // Redirect to login if unauthorized
        }
    });
}
