class LocalStorage {
    static getUsers() {
        return JSON.parse(localStorage.getItem('users') || '[]');
    }

    static saveUser(user) {
        const users = this.getUsers();
        const existingUserIndex = users.findIndex(u => u.email === user.email);
        
        if (existingUserIndex >= 0) {
            users[existingUserIndex] = {...users[existingUserIndex], ...user};
        } else {
            users.push(user);
        }
        
        localStorage.setItem('users', JSON.stringify(users));
    }

    static getUserByEmail(email) {
        return this.getUsers().find(u => u.email === email);
    }

    static getUserByToken(token) {
        return this.getUsers().find(u => u.token === token);
    }

    static getQuestionnaires() {
        return JSON.parse(localStorage.getItem('questionnaires') || '[]');
    }

    static saveQuestionnaire(questionnaire) {
        const questionnaires = this.getQuestionnaires();
        const existingIndex = questionnaires.findIndex(q => q.user_id === questionnaire.user_id);
        
        if (existingIndex >= 0) {
            questionnaires[existingIndex] = questionnaire;
        } else {
            questionnaires.push(questionnaire);
        }
        
        localStorage.setItem('questionnaires', JSON.stringify(questionnaires));
    }

    static getChatHistory() {
        return JSON.parse(localStorage.getItem('chat_history') || '[]');
    }

    static saveChatEntry(chatEntry) {
        const history = this.getChatHistory();
        history.push({...chatEntry, timestamp: new Date().toISOString()});
        localStorage.setItem('chat_history', JSON.stringify(history));
        return history.length; // Return the ID of the new entry
    }

    static updateChatEntry(chatId, updates) {
        const history = this.getChatHistory();
        if (history[chatId - 1]) {
            history[chatId - 1] = {...history[chatId - 1], ...updates};
            localStorage.setItem('chat_history', JSON.stringify(history));
            return true;
        }
        return false;
    }

    static getUserChatHistory(userId) {
        return this.getChatHistory().filter(chat => chat.user_id === userId);
    }
}

// Initialize localStorage if empty
if (!localStorage.getItem('users')) {
    localStorage.setItem('users', '[]');
}
if (!localStorage.getItem('questionnaires')) {
    localStorage.setItem('questionnaires', '[]');
}
if (!localStorage.getItem('chat_history')) {
    localStorage.setItem('chat_history', '[]');
}
