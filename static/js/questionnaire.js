document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('questionnaireForm');
    const sections = document.querySelectorAll('.questionnaire-section');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');
    const progressBar = document.getElementById('progressBar');
    
    let currentSection = 0;
    
    // Add event listeners for learning difficulty selection
    const learningDifficultyInputs = document.querySelectorAll('input[name="learning_difficulty"]');
    const tdahSection = document.getElementById('tdahSection');
    const dyslexiaSection = document.getElementById('dyslexiaSection');

    learningDifficultyInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Hide both sections first
            tdahSection.style.display = 'none';
            dyslexiaSection.style.display = 'none';

            // Show relevant section based on selection
            if (this.value === 'TDAH') {
                tdahSection.style.display = 'block';
            } else if (this.value === 'Dislexia') {
                dyslexiaSection.style.display = 'block';
            }
        });
    });
    
    function showSection(index) {
        // Don't allow skipping to later sections
        if (index > 0 && !validatePreviousSections(index)) {
            showError('Por favor complete las secciones anteriores primero');
            return;
        }
        
        sections.forEach((section, i) => {
            if (section) {
                section.style.display = i === index ? 'block' : 'none';
            }
        });
        
        // Update buttons and progress
        prevBtn.style.display = index === 0 ? 'none' : 'block';
        nextBtn.style.display = index === sections.length - 1 ? 'none' : 'block';
        submitBtn.style.display = index === sections.length - 1 ? 'block' : 'none';
        
        // Update progress bar
        const progress = ((index + 1) / sections.length) * 100;
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `${Math.round(progress)}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        
        currentSection = index;
    }
    
    // Add function to validate previous sections
    function validatePreviousSections(currentIndex) {
        for (let i = 0; i < currentIndex; i++) {
            if (!validateSection(i)) {
                return false;
            }
        }
        return true;
    }
    
    function validateSection(index) {
        const section = sections[index];
        const inputs = section.querySelectorAll('input[type="radio"]');
        const groups = new Set();
        inputs.forEach(input => groups.add(input.name));
        
        for (const group of groups) {
            if (!section.querySelector(`input[name="${group}"]:checked`)) {
                showError('Por favor, responde todas las preguntas de esta sección.');
                return false;
            }
        }
        return true;
    }
    
    prevBtn.addEventListener('click', () => {
        if (currentSection > 0) {
            showSection(currentSection - 1);
        }
    });
    
    nextBtn.addEventListener('click', () => {
        if (validateSection(currentSection)) {
            showSection(currentSection + 1);
        }
    });
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (!validateSection(currentSection)) {
            return;
        }
        
        const formData = {
            study_time: form.querySelector('input[name="study_time"]:checked')?.value,
            session_duration: form.querySelector('input[name="session_duration"]:checked')?.value,
            learning_pace: form.querySelector('input[name="learning_pace"]:checked')?.value,
            learning_style: form.querySelector('input[name="learning_style"]:checked')?.value,
            content_format: form.querySelector('input[name="content_format"]:checked')?.value,
            feedback_preference: form.querySelector('input[name="feedback_preference"]:checked')?.value,
            learning_goals: form.querySelector('input[name="learning_goals"]:checked')?.value,
            motivators: form.querySelector('input[name="motivators"]:checked')?.value,
            challenges: form.querySelector('input[name="challenges"]:checked')?.value,
            interest_areas: form.querySelector('input[name="interest_areas"]:checked')?.value,
            experience_level: form.querySelector('input[name="experience_level"]:checked')?.value,
            learning_tools: form.querySelector('input[name="learning_tools"]:checked')?.value,
            learning_difficulty: form.querySelector('input[name="learning_difficulty"]:checked')?.value
        };

        // Add TDAH responses if applicable
        if (formData.learning_difficulty === 'TDAH') {
            formData.tdah_responses = {
                attention: form.querySelector('input[name="tdah_attention"]:checked')?.value,
                distraction: form.querySelector('input[name="tdah_distraction"]:checked')?.value,
                physical: form.querySelector('input[name="tdah_physical"]:checked')?.value,
                activities: form.querySelector('input[name="tdah_activities"]:checked')?.value,
                concentration: form.querySelector('input[name="tdah_concentration"]:checked')?.value
            };
        }

        // Add Dyslexia responses if applicable
        if (formData.learning_difficulty === 'Dislexia') {
            formData.dyslexia_responses = {
                reading: form.querySelector('input[name="dyslexia_reading"]:checked')?.value,
                content: form.querySelector('input[name="dyslexia_content"]:checked')?.value,
                organization: form.querySelector('input[name="dyslexia_organization"]:checked')?.value,
                speed: form.querySelector('input[name="dyslexia_speed"]:checked')?.value,
                comprehension: form.querySelector('input[name="dyslexia_comprehension"]:checked')?.value
            };
        }
        
        submitQuestionnaire(formData);
    });
    
    // Ensure we start at section 0
    showSection(0);
});

function submitQuestionnaire(formData) {
    const token = localStorage.getItem('token');
    if (!token) {
        showError('No se encontró el token de autorización. Por favor, inicie sesión nuevamente.');
        window.location.href = '/';
        return;
    }

    fetch('/submit_questionnaire', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token
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
            alert('Cuestionario enviado exitosamente. Tu perfil de aprendizaje ha sido identificado.');
            window.location.href = '/dashboard';
        } else {
            throw new Error(data.message || 'Error desconocido');
        }
    })
    .catch((error) => {
        console.error('Error:', error);
        showError('Error al enviar el cuestionario: ' + error.message);
        if (error.message.includes('401')) {
            window.location.href = '/';
        }
    });
}

function showError(message) {
    const errorToast = document.getElementById('errorToast');
    const errorBody = errorToast.querySelector('.toast-body');
    errorBody.textContent = message;
    const toast = new bootstrap.Toast(errorToast);
    toast.show();
}
