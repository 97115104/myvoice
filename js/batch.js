/**
 * My Voice - Batch Generation
 * Generate audio from multiple URLs in a queue
 */

const CORS_PROXIES = [
    'https://api.allorigins.win/raw?url=',
    'https://corsproxy.io/?'
];

const state = {
    voiceData: null,
    voiceFileName: null,
    queue: [], // Array of {id, url, title, status, error}
    isProcessing: false,
    serverUrl: 'http://localhost:5123'
};

// DOM Elements
const elements = {
    voiceFile: document.getElementById('voice-file'),
    fileName: document.getElementById('file-name'),
    audioPreview: document.getElementById('audio-preview'),
    voiceAudio: document.getElementById('voice-audio'),
    btnClearAudio: document.getElementById('btn-clear-audio'),
    outputPath: document.getElementById('output-path'),
    queueContainer: document.getElementById('queue-container'),
    newUrl: document.getElementById('new-url'),
    btnPreview: document.getElementById('btn-preview'),
    btnGenerateAll: document.getElementById('btn-generate-all'),
    btnClearQueue: document.getElementById('btn-clear-queue'),
    progressOverall: document.getElementById('progress-overall'),
    progressStatus: document.getElementById('progress-status'),
    progressCount: document.getElementById('progress-count'),
    progressBar: document.getElementById('progress-bar'),
    language: document.getElementById('language'),
    speed: document.getElementById('speed'),
    speedValue: document.getElementById('speed-value'),
    // Preview modal
    previewModal: document.getElementById('preview-modal'),
    previewTitle: document.getElementById('preview-title'),
    previewContent: document.getElementById('preview-content'),
    previewChars: document.getElementById('preview-chars'),
    btnClosePreview: document.getElementById('btn-close-preview'),
    btnCancelPreview: document.getElementById('btn-cancel-preview'),
    btnConfirmAdd: document.getElementById('btn-confirm-add')
};

// Preview state
let previewData = {
    url: '',
    title: '',
    content: ''
};

// Helper to get output path
function getOutputPath() {
    return elements.outputPath.value.trim() || '/Users/x97115104/Desktop/blog audio/batch';
}

// Initialize
function init() {
    // Voice file handling
    elements.voiceFile.addEventListener('change', handleVoiceFile);
    elements.btnClearAudio.addEventListener('click', clearVoiceFile);
    
    // Preview button
    elements.btnPreview.addEventListener('click', previewUrl);
    elements.newUrl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            previewUrl();
        }
    });
    
    // Preview modal
    elements.btnClosePreview.addEventListener('click', closePreview);
    elements.btnCancelPreview.addEventListener('click', closePreview);
    elements.btnConfirmAdd.addEventListener('click', confirmAddToQueue);
    elements.previewModal.addEventListener('click', (e) => {
        if (e.target === elements.previewModal) closePreview();
    });
    
    // Update char count when content is edited
    elements.previewContent.addEventListener('input', updateCharCount);
    
    // Generate controls
    elements.btnGenerateAll.addEventListener('click', generateAll);
    elements.btnClearQueue.addEventListener('click', clearQueue);
    
    // Speed slider
    elements.speed.addEventListener('input', () => {
        elements.speedValue.textContent = `${elements.speed.value}x`;
    });
    
    updateGenerateButton();
    renderQueue();
}

function updateCharCount() {
    const len = elements.previewContent.value.length;
    elements.previewChars.textContent = len.toLocaleString();
}

// Voice file handling
function handleVoiceFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
        state.voiceData = event.target.result;
        state.voiceFileName = file.name;
        elements.fileName.textContent = file.name;
        elements.voiceAudio.src = event.target.result;
        elements.audioPreview.classList.remove('hidden');
        updateGenerateButton();
    };
    reader.readAsDataURL(file);
}

function clearVoiceFile() {
    state.voiceData = null;
    state.voiceFileName = null;
    elements.voiceFile.value = '';
    elements.fileName.textContent = 'No file selected';
    elements.voiceAudio.src = '';
    elements.audioPreview.classList.add('hidden');
    updateGenerateButton();
}

// Preview functionality
async function previewUrl() {
    const url = elements.newUrl.value.trim();
    
    if (!url) {
        elements.newUrl.focus();
        return;
    }
    
    // Validate URL
    try {
        new URL(url);
    } catch {
        alert('Please enter a valid URL');
        return;
    }
    
    // Show loading state
    elements.btnPreview.disabled = true;
    elements.btnPreview.innerHTML = '<span class="loading-spinner"></span> Fetching...';
    
    try {
        // Fetch content and extract title
        const { content, title } = await fetchUrlWithTitle(url);
        
        // Store preview data
        previewData = {
            url: url,
            title: sanitizeFilename(title),
            content: content
        };
        
        // Populate modal
        elements.previewTitle.value = previewData.title;
        elements.previewContent.value = content;
        updateCharCount();
        
        // Show modal
        elements.previewModal.classList.add('visible');
        
    } catch (error) {
        alert(`Failed to fetch URL: ${error.message}`);
    } finally {
        elements.btnPreview.disabled = false;
        elements.btnPreview.textContent = 'Preview & Add';
    }
}

async function fetchUrlWithTitle(url) {
    let html = '';
    
    // Try server fetch first
    try {
        const response = await fetch(`${state.serverUrl}/api/fetch-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.text) {
                return {
                    content: data.text,
                    title: data.title || generateTitleFromUrl(url)
                };
            }
        }
    } catch (e) {
        console.log('Server fetch failed, trying CORS proxies...');
    }
    
    // Try CORS proxies
    for (const proxy of CORS_PROXIES) {
        try {
            const response = await fetch(proxy + encodeURIComponent(url));
            if (response.ok) {
                html = await response.text();
                break;
            }
        } catch (e) {
            console.log(`Proxy ${proxy} failed, trying next...`);
        }
    }
    
    if (!html) {
        throw new Error('Failed to fetch URL content');
    }
    
    // Parse HTML and extract title + content
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // Extract title
    let title = doc.querySelector('title')?.textContent?.trim() || '';
    // Also try h1 if title is generic
    const h1 = doc.querySelector('h1')?.textContent?.trim();
    if (h1 && (!title || title.length > 100 || title.includes('|'))) {
        title = h1;
    }
    if (!title) {
        title = generateTitleFromUrl(url);
    }
    
    // Extract content
    const content = extractTextFromHtml(html);
    
    return { content, title };
}

function closePreview() {
    elements.previewModal.classList.remove('visible');
    previewData = { url: '', title: '', content: '' };
    
    // Reset modal state
    elements.previewTitle.value = '';
    elements.previewContent.value = '';
    elements.previewChars.textContent = '0';
}

function confirmAddToQueue() {
    // Get values from modal form
    const title = elements.previewTitle.value.trim();
    const content = elements.previewContent.value.trim();
    
    if (!title || !content) {
        alert('Please enter both a filename and content');
        return;
    }
    
    const item = {
        id: Date.now(),
        url: previewData.url || '',
        title: sanitizeFilename(title),
        content: content,
        status: 'pending',
        error: null
    };
    
    state.queue.push(item);
    renderQueue();
    
    // Clear URL input
    elements.newUrl.value = '';
    
    // Close modal
    closePreview();
    
    updateGenerateButton();
}

function generateTitleFromUrl(url) {
    try {
        const pathname = new URL(url).pathname;
        const segments = pathname.split('/').filter(s => s);
        return segments[segments.length - 1] || 'untitled';
    } catch {
        return 'untitled';
    }
}

function sanitizeFilename(name) {
    return name
        .toLowerCase()
        .replace(/[^a-z0-9\-_]/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '')
        .substring(0, 100);
}

function removeFromQueue(id) {
    state.queue = state.queue.filter(item => item.id !== id);
    renderQueue();
    updateGenerateButton();
}

function clearQueue() {
    state.queue = [];
    renderQueue();
    updateGenerateButton();
    elements.progressOverall.classList.add('hidden');
}

function renderQueue() {
    if (state.queue.length === 0) {
        elements.queueContainer.innerHTML = `
            <div class="empty-queue">
                <p>No items in queue. Add URLs above to get started.</p>
            </div>
        `;
        return;
    }
    
    elements.queueContainer.innerHTML = state.queue.map(item => `
        <div class="queue-item ${item.status}" data-id="${item.id}">
            <div>
                <div style="font-weight: 500; margin-bottom: 0.25rem;">${escapeHtml(item.title)}.wav</div>
                <div style="font-size: 12px; color: #888; word-break: break-all;">${escapeHtml(item.url)}</div>
            </div>
            <div style="text-align: center;">
                ${getStatusBadge(item.status)}
            </div>
            <button class="btn-remove" onclick="removeFromQueue(${item.id})" ${item.status === 'processing' ? 'disabled' : ''}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
            ${item.error ? `<div class="queue-status error">${escapeHtml(item.error)}</div>` : ''}
            ${item.status === 'completed' ? `<div class="queue-status success">Saved to ${escapeHtml(item.outputPath || getOutputPath())}/${item.title}.wav</div>` : ''}
        </div>
    `).join('');
}

function getStatusBadge(status) {
    const badges = {
        pending: '<span style="color: #888;">Pending</span>',
        processing: '<span style="color: #27ae60;">⏳ Processing...</span>',
        completed: '<span style="color: #27ae60;">✓ Completed</span>',
        error: '<span style="color: #e74c3c;">✗ Failed</span>'
    };
    return badges[status] || badges.pending;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Generate button state
function updateGenerateButton() {
    const canGenerate = state.voiceData && state.queue.length > 0 && !state.isProcessing;
    elements.btnGenerateAll.disabled = !canGenerate;
    
    if (state.isProcessing) {
        elements.btnGenerateAll.innerHTML = `
            <svg class="icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
            </svg>
            Processing...
        `;
    } else {
        elements.btnGenerateAll.innerHTML = `
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Generate All (${state.queue.length})
        `;
    }
}

// Fetch URL content
async function fetchUrlContent(url) {
    // Try direct fetch first (might work for same-origin or CORS-enabled sites)
    try {
        const response = await fetch(`${state.serverUrl}/api/fetch-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.text) {
                return data.text;
            }
        }
    } catch (e) {
        console.log('Server fetch failed, trying CORS proxies...');
    }
    
    // Try CORS proxies
    for (const proxy of CORS_PROXIES) {
        try {
            const response = await fetch(proxy + encodeURIComponent(url));
            if (response.ok) {
                const html = await response.text();
                return extractTextFromHtml(html);
            }
        } catch (e) {
            console.log(`Proxy ${proxy} failed, trying next...`);
        }
    }
    
    throw new Error('Failed to fetch URL content');
}

function extractTextFromHtml(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    // Remove unwanted elements
    const removeSelectors = [
        'script', 'style', 'noscript', 'nav', 'header', 'footer', 
        'aside', 'iframe', 'form', '.comments', '#comments', 
        '.sidebar', '.navigation', '.menu', '.social-share',
        '.related-posts', '.advertisement', '.ad', '[role="navigation"]',
        '[role="banner"]', '[role="contentinfo"]', '.cookie-notice',
        '.popup', '.modal', '.newsletter', '.subscribe'
    ];
    removeSelectors.forEach(sel => {
        doc.querySelectorAll(sel).forEach(el => el.remove());
    });
    
    // Try to find main content
    const contentSelectors = [
        'article.post-content', 'article .post-content', '.post-content',
        '.entry-content', '.article-content', '.content-body', '.blog-post-content',
        '.body.markup', '.post-content-final', 'article section', 'article',
        '[role="main"]', 'main', '.main-content', '#main-content', '.content', '#content', 'body'
    ];
    
    let contentEl = null;
    for (const selector of contentSelectors) {
        const el = doc.querySelector(selector);
        if (el && el.textContent.trim().length > 200) {
            contentEl = el;
            break;
        }
    }
    
    if (!contentEl) {
        contentEl = doc.body;
    }
    
    // Extract text, preserving paragraph structure
    const blocks = [];
    const blockElements = contentEl.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li, blockquote, pre');
    
    if (blockElements.length > 0) {
        blockElements.forEach(el => {
            const text = el.textContent.trim();
            if (text.length > 0) {
                if (el.tagName.match(/^H[1-6]$/)) {
                    blocks.push('\n' + text + '\n');
                } else if (el.tagName === 'BLOCKQUOTE') {
                    blocks.push('> ' + text);
                } else if (el.tagName === 'PRE') {
                    blocks.push('```\n' + text + '\n```');
                } else if (el.tagName === 'LI') {
                    blocks.push('• ' + text);
                } else {
                    blocks.push(text);
                }
            }
        });
    } else {
        blocks.push(contentEl.textContent.trim());
    }
    
    // Join with double newlines for paragraph separation
    let content = blocks.join('\n\n');
    
    // Clean up excessive whitespace
    content = content
        .replace(/\n{3,}/g, '\n\n')
        .replace(/[ \t]+/g, ' ')
        .trim();
    
    return content.substring(0, 50000);
}

// Generate all items
async function generateAll() {
    if (!state.voiceData || state.queue.length === 0) return;
    
    state.isProcessing = true;
    updateGenerateButton();
    
    // Reset all pending items
    state.queue.forEach(item => {
        if (item.status !== 'completed') {
            item.status = 'pending';
            item.error = null;
        }
    });
    
    // Show progress
    elements.progressOverall.classList.remove('hidden');
    
    const pendingItems = state.queue.filter(item => item.status === 'pending');
    let completed = 0;
    
    for (const item of pendingItems) {
        item.status = 'processing';
        renderQueue();
        updateProgress(completed, pendingItems.length, `Processing: ${item.title}`);
        
        try {
            // Use cached content if available, otherwise fetch
            const text = item.content || await fetchUrlContent(item.url);
            
            if (!text || text.length < 10) {
                throw new Error('No text content found at URL');
            }
            
            // Generate audio
            const formData = new FormData();
            
            // Convert base64 to blob for voice
            const voiceBlob = await fetch(state.voiceData).then(r => r.blob());
            formData.append('voice', voiceBlob, state.voiceFileName || 'voice.wav');
            formData.append('text', text);
            formData.append('language', elements.language.value);
            formData.append('speed', elements.speed.value);
            
            const outputDir = getOutputPath();
            item.outputPath = outputDir;
            formData.append('output_path', `${outputDir}/${item.title}.wav`);
            
            const response = await fetch(`${state.serverUrl}/api/batch-tts`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Generation failed');
            }
            
            const result = await response.json();
            item.status = 'completed';
            completed++;
            
        } catch (error) {
            console.error(`Error processing ${item.title}:`, error);
            item.status = 'error';
            item.error = error.message;
        }
        
        renderQueue();
    }
    
    // Done
    state.isProcessing = false;
    updateGenerateButton();
    updateProgress(completed, pendingItems.length, 'Complete!');
    
    // Show completion summary
    const successCount = state.queue.filter(i => i.status === 'completed').length;
    const errorCount = state.queue.filter(i => i.status === 'error').length;
    elements.progressStatus.textContent = `Done! ${successCount} succeeded, ${errorCount} failed`;
}

function updateProgress(completed, total, status) {
    const percent = total > 0 ? (completed / total) * 100 : 0;
    elements.progressBar.style.width = `${percent}%`;
    elements.progressCount.textContent = `${completed}/${total}`;
    elements.progressStatus.textContent = status;
}

// Make removeFromQueue available globally
window.removeFromQueue = removeFromQueue;

// Start
init();
