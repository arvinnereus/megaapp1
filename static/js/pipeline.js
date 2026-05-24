function pipelineStream() {
    return {
        events: [],
        generating: false,
        contentId: null,
        error: null,

        async generate(inputText, inputType, platform, includeVideo) {
            this.events = [];
            this.generating = true;
            this.error = null;

            try {
                const response = await fetch('/content/api/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        input_text: inputText,
                        input_type: inputType,
                        platform: platform,
                        include_video: includeVideo,
                    }),
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const event = JSON.parse(line.slice(6));
                                this.events.push({
                                    ...event,
                                    timestamp: new Date().toLocaleTimeString(),
                                });

                                if (event.stage === 'done') {
                                    this.generating = false;
                                    if (event.content_id) {
                                        this.contentId = event.content_id;
                                        // Redirect to content library with confetti flag
                                        setTimeout(() => {
                                            window.location.href = '/content?celebrate=1';
                                        }, 2000);
                                    }
                                }

                                // Auto-scroll log
                                this.$nextTick(() => {
                                    const log = this.$refs.pipelineLog;
                                    if (log) log.scrollTop = log.scrollHeight;
                                });
                            } catch (e) {
                                // Skip malformed lines
                            }
                        }
                    }
                }
            } catch (err) {
                this.error = err.message;
                this.generating = false;
            }
        },

        getStatusClass(status) {
            return {
                'success': 'success',
                'error': 'error',
                'polling': 'polling',
                'progress': '',
            }[status] || '';
        },
    };
}
