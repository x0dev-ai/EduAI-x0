class LocalStorage {
    static setItem(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('Error saving to localStorage:', error);
            return false;
        }
    }

    static getItem(key) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : null;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return null;
        }
    }

    static removeItem(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('Error removing from localStorage:', error);
            return false;
        }
    }

    // User-related methods
    static saveUser(userData) {
        return this.setItem('user', userData);
    }

    static getUser() {
        return this.getItem('user');
    }

    // Questionnaire-related methods
    static saveQuestionnaireResponse(response) {
        const responses = this.getItem('questionnaire_responses') || [];
        responses.push({
            ...response,
            timestamp: new Date().toISOString()
        });
        return this.setItem('questionnaire_responses', responses);
    }

    static getQuestionnaireResponses() {
        return this.getItem('questionnaire_responses') || [];
    }

    // Chat history methods
    static saveChatHistory(chatData) {
        const history = this.getItem('chat_history') || [];
        history.push({
            ...chatData,
            timestamp: new Date().toISOString()
        });
        return this.setItem('chat_history', history);
    }

    static getChatHistory() {
        return this.getItem('chat_history') || [];
    }
}
