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

    fetch('/submit_questionnaire', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': localStorage.getItem('token')
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.user_type) {
            alert('Questionnaire submitted successfully. Your user type is: ' + data.user_type);
            window.location.href = '/dashboard';
        } else {
            alert('Error: ' + data.message);
        }
    })
    .catch((error) => {
        console.error('Error:', error);
    });
}
