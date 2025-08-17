// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    // Set up WebSocket handlers for dashboard
    if (window.sketchbookWS) {
        window.sketchbookWS.on('preview_updated', handlePreviewUpdate);
        window.sketchbookWS.on('execution_complete', handleExecutionComplete);
        window.sketchbookWS.on('thumbnail_updated', handleThumbnailUpdate);
    }

    // Add loading states to buttons
    setupButtonLoadingStates();
}

function executeSketch(sketchName) {
    showExecutionLoading(sketchName, true);

    fetch(`/execute/${sketchName}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        showExecutionLoading(sketchName, false);

        if (data.success) {
            showNotification(`"${sketchName}" executed successfully!`, 'success');
            // Refresh the page to show updated preview
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showNotification(`Execution failed: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        showExecutionLoading(sketchName, false);
        console.error('Error executing sketch:', error);
        showNotification('Network error during execution', 'error');
    });
}

function viewCode(sketchName) {
    fetch(`/code/${sketchName}`)
    .then(response => response.text())
    .then(code => {
        showCodeModal(sketchName, code);
    })
    .catch(error => {
        console.error('Error fetching code:', error);
        showNotification('Failed to load code', 'error');
    });
}

function showCodeModal(sketchName, code) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4';
    modal.onclick = (e) => {
        if (e.target === modal) {
            document.body.removeChild(modal);
        }
    };

    // Create modal content
    const modalContent = document.createElement('div');
    modalContent.className = 'bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden';

    modalContent.innerHTML = `
        <div class="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6">
            <div class="flex justify-between items-center">
                <h2 class="text-2xl font-bold">${sketchName}</h2>
                <button onclick="this.closest('.fixed').remove()"
                        class="text-white hover:text-gray-200 text-2xl">&times;</button>
            </div>
        </div>
        <div class="p-6 max-h-[70vh] overflow-auto">
            <pre class="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm"><code class="language-python">${escapeHtml(code)}</code></pre>
        </div>
        <div class="bg-gray-50 p-6 border-t flex justify-end space-x-3">
            <button onclick="copyToClipboard(\`${escapeForJS(code)}\`)"
                    class="btn-secondary">Copy Code</button>
            <button onclick="this.closest('.fixed').remove()"
                    class="btn-primary">Close</button>
        </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);
}

function showExecutionLoading(sketchName, isLoading) {
    const buttons = document.querySelectorAll(`button[onclick*="${sketchName}"]`);
    buttons.forEach(button => {
        if (button.textContent.includes('Execute')) {
            if (isLoading) {
                button.disabled = true;
                button.innerHTML = '<div class="loading-spinner"></div> Executing...';
            } else {
                button.disabled = false;
                button.innerHTML = 'Execute';
            }
        }
    });
}

function setupButtonLoadingStates() {
    // Add hover effects and loading states to buttons
    const executeButtons = document.querySelectorAll('button[onclick*="executeSketch"]');
    executeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 150);
        });
    });
}

function handlePreviewUpdate(data) {
    // Refresh the specific sketch card if it's visible
    const sketchCards = document.querySelectorAll('.preview-card');
    sketchCards.forEach(card => {
        const link = card.querySelector('a[href*="/sketch/"]');
        if (link && link.href.includes(data.sketch_name)) {
            // Add visual indication that preview was updated
            card.style.borderColor = '#10b981';
            card.style.borderWidth = '2px';
            setTimeout(() => {
                card.style.borderColor = '';
                card.style.borderWidth = '';
            }, 2000);
        }
    });
}

function handleExecutionComplete(data) {
    // Update the sketch card to show it has a preview now
    setTimeout(() => window.location.reload(), 1000);
}

function handleThumbnailUpdate(data) {
    updateSketchCardThumbnail(data.sketch_name, data);
}

// Global function for WebSocket integration
window.updateSketchCardThumbnail = function(sketchName, payload) {
    // Find the sketch card by sketch name
    const sketchCards = document.querySelectorAll('.preview-card');
    
    sketchCards.forEach(card => {
        // Look for the sketch name in various places (link href, button onclick, etc.)
        const links = card.querySelectorAll('a[href*="/sketch/"], button[onclick*="executeSketch"]');
        const isMatchingCard = Array.from(links).some(element => {
            return element.href?.includes(`/sketch/${sketchName}`) || 
                   element.getAttribute('onclick')?.includes(`'${sketchName}'`);
        });
        
        if (isMatchingCard) {
            updateThumbnailInCard(card, payload);
        }
    });
};

function updateThumbnailInCard(card, payload) {
    const thumbnailContainer = card.querySelector('.relative.overflow-hidden, .thumbnail-placeholder');
    
    if (!thumbnailContainer) return;
    
    if (payload.success && payload.thumbnail_url) {
        // Replace placeholder with actual thumbnail
        thumbnailContainer.innerHTML = `
            <a href="/sketch/${payload.sketch_name}" class="block relative overflow-hidden group thumbnail-fade-in">
                <img src="${payload.thumbnail_url}" 
                     alt="${payload.sketch_name} preview"
                     class="preview-card-image object-cover transition-transform duration-300 group-hover:scale-105 cursor-pointer"
                     onerror="this.parentElement.innerHTML='<div class=\\'thumbnail-placeholder thumbnail-error\\'><div class=\\'text-4xl mb-2\\'>⚠</div><div class=\\'text-sm text-gray-600\\'>Preview Error</div></div>'">
                <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all duration-300 flex items-center justify-center">
                    <div class="opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-white bg-opacity-90 px-3 py-2 rounded-lg text-sm font-medium text-gray-800">
                        Open Live Preview
                    </div>
                </div>
            </a>
        `;
    } else if (!payload.success) {
        // Show error state
        thumbnailContainer.innerHTML = `
            <a href="/sketch/${payload.sketch_name}" class="block thumbnail-placeholder thumbnail-error cursor-pointer hover:bg-opacity-80 transition-all duration-300">
                <div class="text-4xl mb-2">⚠</div>
                <div class="text-sm text-red-600">Thumbnail failed</div>
                <div class="text-xs text-red-500 mt-1">${payload.error || 'Unknown error'}</div>
                <div class="text-xs text-gray-500 mt-2">Click to open live preview</div>
            </a>
        `;
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeForJS(text) {
    return text.replace(/`/g, '\\`').replace(/\$/g, '\\$').replace(/\\/g, '\\\\');
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Code copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy code', 'error');
    });
}

function showNotification(message, type = 'info') {
    // Use the WebSocket notification system if available
    if (window.sketchbookWS) {
        window.sketchbookWS.showNotification(message, type);
    } else {
        // Fallback notification
        alert(message);
    }
}
