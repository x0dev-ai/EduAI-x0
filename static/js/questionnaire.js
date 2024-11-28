document.addEventListener('DOMContentLoaded', () => {
    const questionnaireForm = document.getElementById('questionnaireForm');
    
    if (questionnaireForm) {
        questionnaireForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                study_time: document.querySelector('input[name="study_time"]:checked').value,
                session_duration: document.querySelector('input[name="session_duration"]:checked').value,
                learning_pace: document.querySelector('input[name="learning_pace"]:checked').value,
                learning_style: document.querySelector('input[name="learning_style"]:checked').value,
                content_format: document.querySelector('input[name="content_format"]:checked').value,
                feedback_preference: document.querySelector('input[name="feedback_preference"]:checked').value,
                learning_goals: document.querySelector('input[name="learning_goals"]:checked').value,
                motivators: document.querySelector('input[name="motivators"]:checked').value,
                challenges: document.querySelector('input[name="challenges"]:checked').value,
                interest_areas: document.querySelector('input[name="interest_areas"]:checked').value,
                experience_level: document.querySelector('input[name="experience_level"]:checked').value,
                learning_tools: document.querySelector('input[name="learning_tools"]:checked').value
            };

            try {
                const response = await fetch('/submit_questionnaire', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': localStorage.getItem('token')
                    },
                    body: JSON.stringify(formData)
                });

                const data = await response.json();

                if (response.ok) {
                    // Save to localStorage
                    LocalStorage.saveQuestionnaireResponse({
                        ...formData,
                        user_type: data.user_type
                    });

                    // Update user data in localStorage
                    const userData = LocalStorage.getUser();
                    if (userData) {
                        userData.questionnaire_completed = true;
                        userData.user_type = data.user_type;
                        LocalStorage.saveUser(userData);
                    }

                    alert('Cuestionario enviado exitosamente');
                    window.location.href = '/dashboard';
                } else {
                    throw new Error(data.error || 'Error al enviar el cuestionario');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Error al enviar el cuestionario: ' + error.message);
            }
        });
    }
});
