/**
 * AI Chat Panel - Alpine.js data provider + helper functions
 * Loaded by base_admin.html, merged into the parent Alpine scope
 */
function chatAdminData() {
    return {
        chatMessages: [],
        chatInput: '',
        chatLoading: false,

        chatSavHistory() {
            localStorage.setItem('crm-chat-history', JSON.stringify(this.chatMessages.slice(-50)));
        },

        chatScrollBottom() {
            const container = this.$refs.chatMessages;
            if (container) container.scrollTop = container.scrollHeight;
        },

        async chatSend() {
            const message = this.chatInput.trim();
            if (!message || this.chatLoading) return;

            this.chatMessages.push({ role: 'user', content: message, timestamp: new Date().toISOString() });
            this.chatInput = '';
            this.chatLoading = true;
            this.chatSavHistory();
            this.$nextTick(() => this.chatScrollBottom());

            try {
                const history = this.chatMessages.slice(-11, -1).map(m => ({ role: m.role, content: m.content }));
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message, history })
                });
                if (!response.ok) throw new Error('HTTP ' + response.status);
                const data = await response.json();

                this.chatMessages.push({
                    role: 'assistant',
                    content: data.response || "I couldn't process that request.",
                    actions: data.actions_taken || [],
                    timestamp: new Date().toISOString()
                });

                if (data.actions_taken && data.actions_taken.some(a => a.success)) {
                    window.dispatchEvent(new CustomEvent('crm-data-changed', {
                        detail: { actions: data.actions_taken }
                    }));
                }
            } catch (error) {
                this.chatMessages.push({
                    role: 'assistant',
                    content: 'Sorry, I encountered an error. Please check your OpenRouter API key and try again.',
                    timestamp: new Date().toISOString()
                });
            }

            this.chatLoading = false;
            this.chatSavHistory();
            this.$nextTick(() => this.chatScrollBottom());
        }
    };
}

function chatFormatMessage(content) {
    if (!content) return '';
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code style="background: rgba(199,163,90,0.15); padding: 2px 6px; border-radius: 4px; font-size: 0.85em;">$1</code>')
        .replace(/^[\u2022\-]\s+(.+)$/gm, '<div style="padding-left: 16px; position: relative;"><span style="position: absolute; left: 0; color: var(--gold);">\u2022</span>$1</div>')
        .replace(/\n/g, '<br>');
}

function chatFormatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
    if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
    return date.toLocaleDateString();
}
