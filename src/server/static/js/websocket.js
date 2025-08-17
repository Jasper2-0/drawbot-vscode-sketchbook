// WebSocket connection utilities
class SketchbookWebSocket {
    constructor() {
        this.socket = null;
        this.reconnectInterval = 1000;
        this.maxReconnectAttempts = 5;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.messageHandlers = new Map();
    }

    connect(url = null) {
        if (!url) {
            // For sketch preview pages, use the sketch-specific endpoint
            if (window.currentSketchName) {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                url = `${protocol}//${window.location.host}/live/${window.currentSketchName}`;
            } else {
                // Fallback for general pages (though we don't have a general WS endpoint)
                console.warn('No currentSketchName set, WebSocket connection may fail');
                return;
            }
        }

        try {
            this.socket = new WebSocket(url);
            this.setupEventHandlers();
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }

    setupEventHandlers() {
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.onConnectionChange(true);
        };

        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.onConnectionChange(false);
            this.scheduleReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
    }

    handleMessage(data) {
        const { type, ...payload } = data;

        // Call registered handlers for this message type
        if (this.messageHandlers.has(type)) {
            const handlers = this.messageHandlers.get(type);
            handlers.forEach(handler => handler(payload));
        }

        // Built-in message handlers
        switch (type) {
            case 'preview_updated':
                this.onPreviewUpdated(payload);
                break;
            case 'execution_complete':
                this.onExecutionComplete(payload);
                break;
            case 'execution_error':
                this.onExecutionError(payload);
                break;
            case 'thumbnail_updated':
                this.onThumbnailUpdated(payload);
                break;
            default:
                console.log('Unhandled WebSocket message:', data);
        }
    }

    // Event handler registration
    on(messageType, handler) {
        if (!this.messageHandlers.has(messageType)) {
            this.messageHandlers.set(messageType, []);
        }
        this.messageHandlers.get(messageType).push(handler);
    }

    off(messageType, handler) {
        if (this.messageHandlers.has(messageType)) {
            const handlers = this.messageHandlers.get(messageType);
            const index = handlers.indexOf(handler);
            if (index > -1) {
                handlers.splice(index, 1);
            }
        }
    }

    // Built-in event handlers (can be overridden)
    onConnectionChange(connected) {
        // Update UI to show connection status
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
            statusElement.className = connected ? 'status-success' : 'status-error';
        }
    }

    onPreviewUpdated(payload) {
        console.log('Preview updated:', payload);
        // Default behavior - reload current preview if it matches
        if (window.currentSketchName && payload.sketch_name === window.currentSketchName) {
            window.location.reload();
        }
    }

    onExecutionComplete(payload) {
        console.log('Execution completed:', payload);
        this.showNotification('Sketch executed successfully', 'success');
    }

    onExecutionError(payload) {
        console.error('Execution error:', payload);
        this.showNotification(`Execution failed: ${payload.error}`, 'error');
    }

    onThumbnailUpdated(payload) {
        console.log('Thumbnail updated:', payload);
        
        // Update thumbnail in sketch cards if on dashboard
        if (typeof updateSketchCardThumbnail === 'function') {
            updateSketchCardThumbnail(payload.sketch_name, payload);
        }
        
        // Show notification for successful thumbnail generation
        if (payload.success && payload.thumbnail_url) {
            this.showNotification(`Thumbnail ready for "${payload.sketch_name}"`, 'success');
        } else if (!payload.success) {
            console.warn(`Thumbnail generation failed for ${payload.sketch_name}:`, payload.error);
        }
    }

    // Utility methods
    send(type, data = {}) {
        if (this.isConnected && this.socket) {
            this.socket.send(JSON.stringify({ type, ...data }));
        } else {
            console.warn('Cannot send message: WebSocket not connected');
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
            setTimeout(() => this.connect(), this.reconnectInterval);
            this.reconnectInterval = Math.min(this.reconnectInterval * 2, 30000); // Exponential backoff
        } else {
            console.log('Max reconnect attempts reached');
        }
    }

    showNotification(message, type = 'info') {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 status-${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// Global WebSocket instance
window.sketchbookWS = new SketchbookWebSocket();

// Auto-connect when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.sketchbookWS.connect();
});
