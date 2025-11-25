// AFG Bank Assistant - Chat Interface Logic

const messagesContainer = document.getElementById('messages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const loadingIndicator = document.getElementById('loading');
const modelBtn = document.getElementById('modelBtn');
const modelDropdown = document.getElementById('modelDropdown');
const modelName = document.getElementById('modelName');

let currentModel = 'qwen14b';

// Auto-resize textarea
messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
});

// Handle Enter key (Shift+Enter for new line)
messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
});

// Handle form submission
chatForm.addEventListener('submit', async function(e) {
    e.preventDefault();

    const message = messageInput.value.trim();
    if (!message) return;

    // Add user message to UI
    addMessage(message, 'user');

    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Disable input while processing
    setInputState(false);

    // Show loading indicator
    loadingIndicator.style.display = 'flex';
    scrollToBottom();

    try {
        // Send message to API with longer timeout for first request
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 60000); // 60 second timeout

        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message }),
            signal: controller.signal
        });

        clearTimeout(timeout);

        const data = await response.json();

        if (response.ok) {
            // Add assistant response
            addMessage(data.response, 'assistant');
        } else {
            // Show error
            addMessage(
                `Désolé, une erreur est survenue: ${data.error || 'Erreur inconnue'}`,
                'assistant',
                true
            );
        }
    } catch (error) {
        console.error('Error:', error);
        addMessage(
            'Désolé, je ne peux pas me connecter au serveur. Veuillez réessayer.',
            'assistant',
            true
        );
    } finally {
        // Hide loading and re-enable input
        loadingIndicator.style.display = 'none';
        setInputState(true);
        messageInput.focus();
    }
});

// Handle suggestion chips
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('suggestion-chip')) {
        const message = e.target.getAttribute('data-message');
        messageInput.value = message;
        chatForm.dispatchEvent(new Event('submit'));
    }
});

// Handle clear button
clearBtn.addEventListener('click', async function() {
    if (!confirm('Voulez-vous vraiment effacer la conversation ?')) {
        return;
    }

    try {
        const response = await fetch('/api/clear', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            // Clear messages
            messagesContainer.innerHTML = '';

            // Add welcome message back
            addMessage(
                'Bonjour ! Je suis votre assistant AFG Bank. Comment puis-je vous aider aujourd\'hui ?',
                'assistant',
                false,
                true
            );
        }
    } catch (error) {
        console.error('Error clearing history:', error);
        alert('Erreur lors de la réinitialisation de la conversation');
    }
});

// Add message to UI
function addMessage(text, sender, isError = false, showSuggestions = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatar = sender === 'user' ? '👤' : '🏦';

    const contentHTML = `
        <div class="message-content">
            <div class="message-avatar">${avatar}</div>
            <div class="message-text">
                ${isError ? `<div class="error-message">${text}</div>` : `<p>${formatMessage(text)}</p>`}
                <div class="message-time">${new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</div>
                ${showSuggestions ? getSuggestionsHTML() : ''}
            </div>
        </div>
    `;

    messageDiv.innerHTML = contentHTML;
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

// Format message text (basic markdown support)
function formatMessage(text) {
    // Convert newlines to <br>
    text = text.replace(/\n/g, '<br>');

    // Bold: **text** or __text__
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Italic: *text* or _text_
    text = text.replace(/\*(.+?)\*/g, '<em>$1</em>');
    text = text.replace(/_(.+?)_/g, '<em>$1</em>');

    // Code: `code`
    text = text.replace(/`(.+?)`/g, '<code>$1</code>');

    return text;
}

// Get suggestions HTML
function getSuggestionsHTML() {
    return `
        <div class="suggestions">
            <button class="suggestion-chip" data-message="Combien coûte une attestation de clôture de compte ?">💰 Tarifs</button>
            <button class="suggestion-chip" data-message="Quel est mon solde ?">💳 Mon solde</button>
            <button class="suggestion-chip" data-message="Je veux faire un virement">📤 Virement</button>
            <button class="suggestion-chip" data-message="Comment ouvrir un compte ?">ℹ️ Informations</button>
        </div>
    `;
}

// Enable/disable input
function setInputState(enabled) {
    messageInput.disabled = !enabled;
    sendBtn.disabled = !enabled;
}

// Scroll to bottom
function scrollToBottom() {
    setTimeout(() => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }, 100);
}

// Model selector
modelBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    modelDropdown.classList.toggle('show');
});

// Handle model selection
document.querySelectorAll('.model-option').forEach(option => {
    option.addEventListener('click', function() {
        const model = this.getAttribute('data-model');
        currentModel = model;

        // Update UI
        document.querySelectorAll('.model-option').forEach(opt => opt.classList.remove('active'));
        this.classList.add('active');

        // Update button text
        const name = this.querySelector('.model-option-name').textContent;
        modelName.textContent = name;

        // Close dropdown
        modelDropdown.classList.remove('show');

        // Show notification
        addMessage(
            `Modèle changé vers ${name}`,
            'assistant',
            false,
            false
        );
    });
});

// Close dropdown when clicking outside
document.addEventListener('click', function() {
    modelDropdown.classList.remove('show');
});

// Initial focus
messageInput.focus();
