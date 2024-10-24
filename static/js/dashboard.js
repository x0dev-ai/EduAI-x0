document.addEventListener('DOMContentLoaded', function() {
    loadUserProfile();
    setupChatInterface();
});

function loadUserProfile() {
    fetch('/learning_report', {
        headers: {
            'Authorization': localStorage.getItem('token')
        }
    })
    .then(response => response.json())
    .then(data => {
        // Update email
        document.getElementById('userEmail').textContent = data.email;

        // Update profile progress
        const progressBar = document.getElementById('profileProgress');
        progressBar.style.width = `${data.progress || 0}%`;
        progressBar.textContent = `${data.progress || 0}%`;

        // Update learning style
        const learningStyle = document.getElementById('learningStyle');
        learningStyle.textContent = data.learning_style || 'No definido';

        // Update statistics
        updateStatistics(data);
    })
    .catch(error => {
        console.error('Error loading learning report:', error);
        showError('Error al cargar el reporte de aprendizaje');
    });
}

function updateStatistics(data) {
    // Update session count
    const sessionCount = document.querySelector('.col-md-3:nth-child(2) .fs-3');
    sessionCount.textContent = data.completed_questions || '0';

    // Update study time (if available)
    const studyTime = document.querySelector('.col-md-3:nth-child(1) .fs-3');
    if (data.total_study_time) {
        const hours = Math.floor(data.total_study_time / 3600);
        studyTime.textContent = `${hours}h`;
    }

    // Update streak (if available)
    const streak = document.querySelector('.col-md-3:nth-child(3) .fs-3');
    if (data.current_streak) {
        streak.textContent = `${data.current_streak} días`;
    }

    // Update last session
    const lastSession = document.querySelector('.col-md-3:nth-child(4) .text-muted');
    if (data.last_session) {
        const date = new Date(data.last_session);
        lastSession.textContent = date.toLocaleDateString('es-ES', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

// Rest of your existing dashboard.js code...
