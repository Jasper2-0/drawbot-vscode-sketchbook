// Sketch preview page functionality
let ws = null;
let wsConnected = false;
let currentSketchName = null;

function initializeSketchPreview(sketchName) {
    currentSketchName = sketchName;

    // Set up WebSocket handlers for sketch preview
    if (window.sketchbookWS) {
        window.sketchbookWS.on('preview_updated', handlePreviewUpdate);
        window.sketchbookWS.on('execution_started', handleExecutionStarted);
        window.sketchbookWS.on('execution_complete', handleExecutionComplete);
        window.sketchbookWS.on('execution_error', handleExecutionError);
    }

    // Override WebSocket connection for sketch-specific endpoint
    connectSketchWebSocket(sketchName);

    // Scale initial image on page load
    const initialImg = document.getElementById('preview-image');
    if (initialImg) {
        scaleImageForRetina(initialImg);
    }
}

function connectSketchWebSocket(sketchName) {
    // Close existing connection if any
    if (ws) {
        ws.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/live/${sketchName}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = function(event) {
        wsConnected = true;
        updateWSStatus(true);
        updateStatus('🔗 Live preview connected', 'success');
        console.log('WebSocket connected for sketch:', sketchName);
    };

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = function(event) {
        wsConnected = false;
        updateWSStatus(false);
        updateStatus('🔌 Live preview disconnected', 'error');
        console.log('WebSocket disconnected');

        // Attempt to reconnect after 3 seconds
        setTimeout(() => connectSketchWebSocket(sketchName), 3000);
    };

    ws.onerror = function(error) {
        wsConnected = false;
        updateWSStatus(false);
        console.error('WebSocket error:', error);
        updateStatus('❌ Connection error', 'error');
    };
}

function handleWebSocketMessage(data) {
    console.log('WebSocket message:', data);

    switch(data.type) {
        case 'connection_confirmed':
            updateStatus('✅ Live preview active', 'success');
            break;

        case 'execution_started':
            updateStatus('⚡ Executing sketch...', 'info');
            break;

        case 'preview_updated':
            if (data.status === 'success') {
                updateStatus(`✅ Updated! (${data.execution_time?.toFixed(3) || '?'}s)`, 'success');
                updatePreviewImage(data.image_url);
            }
            break;

        case 'execution_error':
            updateStatus(`❌ Error: ${data.error}`, 'error');
            showErrorPlaceholder(data.error);
            break;

        case 'no_preview':
            updateStatus('ℹ️ No preview available', 'info');
            break;
    }
}

function updateStatus(message, type) {
    const statusDiv = document.getElementById('status');
    let className = 'p-4 rounded-lg border-l-4 shadow-md mb-4';
    let icon = '💡';

    if (type === 'success') {
        className += ' bg-green-50 border-green-400 text-green-800';
        icon = '✅';
    } else if (type === 'error') {
        className += ' bg-red-50 border-red-400 text-red-800';
        icon = '❌';
    } else if (type === 'info') {
        className += ' bg-blue-50 border-blue-400 text-blue-800';
        icon = '💡';
    }

    statusDiv.innerHTML = `<div class="${className}">
        <div class="flex items-center gap-2">
            <span class="text-lg">${icon}</span>
            <span class="font-medium">${message}</span>
        </div>
    </div>`;
}

function updateWSStatus(connected) {
    const wsStatus = document.getElementById('ws-status');
    const statusText = document.getElementById('ws-status-text');

    if (connected) {
        wsStatus.className = 'ws-status connected px-3 py-1 rounded-full text-xs font-medium';
        statusText.textContent = 'Connected';
    } else {
        wsStatus.className = 'ws-status disconnected px-3 py-1 rounded-full text-xs font-medium';
        statusText.textContent = 'Disconnected';
    }
}

function scaleImageForRetina(img) {
    // Scale down high-resolution image by 1/3 for retina display
    img.onload = function() {
        const retinaScale = 3.0;
        img.style.width = (this.naturalWidth / retinaScale) + 'px';
        img.style.height = (this.naturalHeight / retinaScale) + 'px';
    };
}

function updatePreviewImage(imageUrl) {
    if (!imageUrl) return;

    // Check if this is a multi-page layout
    const previewContent = document.getElementById('preview-content');
    const isMultiPage = previewContent && previewContent.innerHTML.includes('Multi-page:');

    if (isMultiPage) {
        // Don't override multi-page layouts with single-page updates
        console.log('Skipping single-page update for multi-page layout');
        return;
    }

    const previewImg = document.getElementById('preview-image');
    if (previewImg) {
        previewImg.src = imageUrl + '&t=' + Date.now();
        scaleImageForRetina(previewImg);
    } else {
        // Create new image element
        previewContent.innerHTML = `
            <div class="relative inline-block">
                <img src="${imageUrl}&t=${Date.now()}" alt="${currentSketchName} preview"
                     class="preview-image" id="preview-image">
                <div class="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-1 rounded-full shadow-lg">
                    ✨ Latest
                </div>
            </div>
            <div class="text-sm text-slate-500 mt-4 bg-slate-50 px-4 py-2 rounded-lg">
                <span class="font-medium">Updated:</span> Just now
            </div>
        `;
        const newImg = document.getElementById('preview-image');
        scaleImageForRetina(newImg);
    }
}

function showErrorPlaceholder(errorMessage) {
    const previewContent = document.getElementById('preview-content');
    const errorDetails = errorMessage.split('\n');
    const errorType = errorDetails[0].includes(':') ? errorDetails[0].split(':')[0] : 'Error';
    const errorDescription = errorDetails[0].includes(':') ? errorDetails[0].split(':').slice(1).join(':').trim() : errorMessage;

    previewContent.innerHTML = `
        <div class="error-placeholder">
            <div class="error-icon">🚫</div>
            <h3 class="error-title">Sketch Execution Failed</h3>
            <div class="bg-white rounded-lg p-4 mb-4 border border-red-200">
                <div class="text-sm font-mono text-red-700 mb-2">
                    <span class="font-bold">${errorType}:</span> ${errorDescription}
                </div>
                ${errorDetails.length > 1 ? `
                    <details class="text-xs text-red-600 mt-2">
                        <summary class="cursor-pointer hover:text-red-800">Show full error details</summary>
                        <pre class="mt-2 text-left whitespace-pre-wrap">${errorDetails.slice(1).join('\n')}</pre>
                    </details>
                ` : ''}
            </div>
            <div class="error-tips">
                <p class="font-medium">Common fixes:</p>
                <ul class="text-left space-y-1 max-w-md mx-auto">
                    <li>• Check for syntax errors (missing quotes, parentheses, indentation)</li>
                    <li>• Verify DrawBot import: <code class="bg-red-100 px-1 rounded">import drawBot as drawbot</code></li>
                    <li>• Ensure consistent variable naming throughout the script</li>
                    <li>• Check that all functions are called correctly</li>
                </ul>
            </div>
            <div class="mt-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p class="text-sm text-yellow-800">
                    💡 <strong>Tip:</strong> Fix the Python errors in your sketch file, then press "Execute Sketch" to retry.
                </p>
            </div>
        </div>
    `;
}

async function executeSketch() {
    if (!currentSketchName) return;

    try {
        updateStatus('⚡ Executing sketch...', 'info');

        const response = await fetch(`/execute/${currentSketchName}`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.status === 'success') {
            updateStatus(`✅ Manual execution: ${result.execution_time}s`, 'success');
            if (result.preview_url) {
                updatePreviewImage(result.preview_url);
            }
        } else {
            updateStatus(`❌ Error: ${result.error}`, 'error');
            showErrorPlaceholder(result.error);
        }
    } catch (error) {
        updateStatus(`❌ Network error: ${error.message}`, 'error');
    }
}

function forceRefresh() {
    if (ws && wsConnected) {
        ws.send(JSON.stringify({type: 'force_refresh'}));
    } else {
        updateStatus('❌ WebSocket not connected', 'error');
    }
}

// Event handlers for general sketch preview functionality
function handlePreviewUpdate(data) {
    if (data.sketch_name === currentSketchName) {
        updatePreviewImage(data.image_url);
    }
}

function handleExecutionStarted(data) {
    if (data.sketch_name === currentSketchName) {
        updateStatus('⚡ Executing sketch...', 'info');
    }
}

function handleExecutionComplete(data) {
    if (data.sketch_name === currentSketchName) {
        updateStatus(`✅ Execution completed (${data.execution_time || '?'}s)`, 'success');
    }
}

function handleExecutionError(data) {
    if (data.sketch_name === currentSketchName) {
        updateStatus(`❌ Execution failed: ${data.error}`, 'error');
        showErrorPlaceholder(data.error);
    }
}
