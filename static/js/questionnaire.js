document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('questionnaireForm');
    const sections = document.querySelectorAll('.questionnaire-section');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const submitBtn = document.getElementById('submitBtn');
    const progressBar = document.getElementById('progressBar');
    
    let currentSection = 0;
    let sectionValidations = new Array(sections.length).fill(false);
    
    function showSection(index) {
        if (!sections || !sections.length) return;
        
        // Ensure we can't skip sections
        if (index > 0 && !sectionValidations[index - 1]) {
            showError('Por favor, complete la sección anterior antes de continuar.');
            return;
        }
        
        sections.forEach((section, i) => {
            if (section) {
                section.style.display = i === index ? 'block' : 'none';
            }
        });
        
        // Update buttons
        if (prevBtn) {
            prevBtn.style.display = index === 0 ? 'none' : 'block';
        }
        if (nextBtn) {
            nextBtn.style.display = index === sections.length - 1 ? 'none' : 'block';
        }
        if (submitBtn) {
            submitBtn.style.display = index === sections.length - 1 && sectionValidations[index] ? 'block' : 'none';
        }
        
        // Update progress bar
        if (progressBar) {
            const progress = ((index + 1) / sections.length) * 100;
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${Math.round(progress)}%`;
            progressBar.setAttribute('aria-valuenow', progress);
        }
        
        currentSection = index;
        saveCurrentState();
    }

    // Handle learning difficulty selection
    const learningDifficultyInputs = document.querySelectorAll('input[name="learning_difficulty"]');
    const tdahQuestions = document.getElementById('tdahQuestions');
    const dyslexiaQuestions = document.getElementById('dyslexiaQuestions');

    learningDifficultyInputs.forEach(input => {
        input.addEventListener('change', function() {
            tdahQuestions.style.display = 'none';
            dyslexiaQuestions.style.display = 'none';
            
            if (this.value === 'TDAH') {
                tdahQuestions.style.display = 'block';
            } else if (this.value === 'dislexia') {
                dyslexiaQuestions.style.display = 'block';
            }
            validateSection(currentSection);
        });
    });
    
    function validateSection(index) {
        if (!sections || !sections[index]) return false;
        
        const section = sections[index];
        const inputs = section.querySelectorAll('input[type="radio"], select');
        const groups = new Set();
        let isValid = true;
        
        inputs.forEach(input => {
            if (input.style.display !== 'none' && input.closest('div').style.display !== 'none') {
                groups.add(input.name);
            }
        });
        
        for (const group of groups) {
            const selectedInput = section.querySelector(`input[name="${group}"]:checked, select[name="${group}"]`);
            if (!selectedInput || !selectedInput.value) {
                isValid = false;
                break;
            }
        }

        // Special validation for learning difficulties section
        if (section.id === 'section5') {
            const learningDifficulty = section.querySelector('input[name="learning_difficulty"]:checked');
            if (!learningDifficulty) {
                isValid = false;
            } else {
                if (learningDifficulty.value === 'TDAH') {
                    const tdahQuestions = section.querySelectorAll('#tdahQuestions select');
                    tdahQuestions.forEach(select => {
                        if (!select.value) isValid = false;
                    });
                } else if (learningDifficulty.value === 'dislexia') {
                    const dyslexiaQuestions = section.querySelectorAll('#dyslexiaQuestions select');
                    dyslexiaQuestions.forEach(select => {
                        if (!select.value) isValid = false;
                    });
                }
            }
        }

        sectionValidations[index] = isValid;
        updateButtons();
        return isValid;
    }
    
    function updateButtons() {
        if (nextBtn) {
            nextBtn.disabled = !sectionValidations[currentSection];
        }
        if (submitBtn && currentSection === sections.length - 1) {
            submitBtn.style.display = sectionValidations[currentSection] ? 'block' : 'none';
        }
    }
    
    function saveCurrentState() {
        const formData = {};
        const inputs = form.querySelectorAll('input[type="radio"]:checked, select');
        inputs.forEach(input => {
            formData[input.name] = input.value;
        });
        sessionStorage.setItem('questionnaireState', JSON.stringify({
            currentSection,
            formData,
            sectionValidations
        }));
    }
    
    function restoreState() {
        const savedState = sessionStorage.getItem('questionnaireState');
        if (savedState) {
            try {
                const state = JSON.parse(savedState);
                currentSection = state.currentSection || 0;
                sectionValidations = state.sectionValidations || new Array(sections.length).fill(false);
                
                // Restore form values
                if (state.formData) {
                    Object.entries(state.formData).forEach(([name, value]) => {
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
                
                showSection(currentSection);
                validateSection(currentSection);
            } catch (error) {
                console.error('Error restoring state:', error);
                sessionStorage.removeItem('questionnaireState');
                showSection(0);
            }
        } else {
            showSection(0);
        }
    }
    
    // Add input event listeners for validation
    sections.forEach((section, index) => {
        const inputs = section.querySelectorAll('input[type="radio"], select');
        inputs.forEach(input => {
            input.addEventListener('change', () => {
                validateSection(index);
                saveCurrentState();
            });
        });
    });
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentSection > 0) {
                showSection(currentSection - 1);
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (validateSection(currentSection)) {
                showSection(currentSection + 1);
            } else {
                showError('Por favor, completa todas las preguntas de esta sección antes de continuar.');
            }
        });
    }
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (!validateSection(currentSection)) {
                showError('Por favor, completa todas las preguntas antes de enviar.');
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

            // Add difficulty-specific details based on selection
            if (formData.learning_difficulty === 'TDAH') {
                formData.difficulty_details = {
                    attention: form.querySelector('select[name="tdah_attention"]')?.value,
                    distraction: form.querySelector('select[name="tdah_distraction"]')?.value,
                    physical_restlessness: form.querySelector('select[name="tdah_physical_restlessness"]')?.value,
                    activity_preference: form.querySelector('select[name="tdah_activity_preference"]')?.value,
                    concentration_time: form.querySelector('select[name="tdah_concentration_time"]')?.value
                };
            } else if (formData.learning_difficulty === 'dislexia') {
                formData.difficulty_details = {
                    reading_difficulty: form.querySelector('select[name="dyslexia_reading_difficulty"]')?.value,
                    content_preference: form.querySelector('select[name="dyslexia_content_preference"]')?.value,
                    organization: form.querySelector('select[name="dyslexia_organization"]')?.value,
                    reading_speed: form.querySelector('select[name="dyslexia_reading_speed"]')?.value,
                    comprehension: form.querySelector('select[name="dyslexia_comprehension"]')?.value
                };
            }
            
            submitQuestionnaire(formData);
        });
    }
    
    // Initialize the form
    restoreState();
});

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
            return response.json().then(data => {
                throw new Error(data.error || 'Error en la respuesta del servidor');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.user_type) {
            // Clear questionnaire state before redirecting
            sessionStorage.removeItem('questionnaireState');
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
