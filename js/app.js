/**
 * My Voice - Voice Cloning & Text-to-Speech
 * Frontend Application
 * 
 * Runs locally using a Python TTS server
 * No data leaves your computer
 */

// CORS Proxies for URL fetching (same as whodoneit)
const CORS_PROXIES = [
    'https://api.allorigins.win/raw?url=',
    'https://corsproxy.io/?'
];

// State
const state = {
    voiceData: null,
    voiceFileName: null,
    generatedAudio: null,
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    serverUrl: 'http://localhost:5123'
};

// DOM Elements
const elements = {
    // Voice input
    voiceFile: document.getElementById('voice-file'),
    fileName: document.getElementById('file-name'),
    btnRecord: document.getElementById('btn-record'),
    recordIcon: document.getElementById('record-icon'),
    stopIcon: document.getElementById('stop-icon'),
    recordText: document.getElementById('record-text'),
    recordStatus: document.getElementById('record-status'),
    audioPreview: document.getElementById('audio-preview'),
    voiceAudio: document.getElementById('voice-audio'),
    btnClearAudio: document.getElementById('btn-clear-audio'),
    
    // Text input
    textTabBtns: document.querySelectorAll('.text-tab-btn'),
    textPanel: document.getElementById('text-panel'),
    urlPanel: document.getElementById('url-panel'),
    textInput: document.getElementById('text-input'),
    charCount: document.getElementById('char-count'),
    urlInput: document.getElementById('url-input'),
    btnFetchUrl: document.getElementById('btn-fetch-url'),
    fetchText: document.getElementById('fetch-text'),
    urlStatus: document.getElementById('url-status'),
    
    // Generate
    btnGenerate: document.getElementById('btn-generate'),
    generateIcon: document.getElementById('generate-icon'),
    generateText: document.getElementById('generate-text'),
    generateSpinner: document.getElementById('generate-spinner'),
    progressContainer: document.getElementById('progress-container'),
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    
    // Settings
    languageSelect: document.getElementById('language-select'),
    speedSlider: document.getElementById('speed-slider'),
    speedValue: document.getElementById('speed-value'),
    
    // Output
    outputSection: document.getElementById('output-section'),
    outputAudio: document.getElementById('output-audio'),
    btnDownload: document.getElementById('btn-download'),
    btnShare: document.getElementById('btn-share'),
    
    // Settings panel
    btnToggleSettings: document.getElementById('btn-toggle-settings'),
    settingsContent: document.getElementById('settings-content'),
    serverUrlInput: document.getElementById('server-url'),
    
    // Server status
    statusDot: document.getElementById('status-dot'),
    statusText: document.getElementById('status-text'),
    
    // Modals
    infoModal: document.getElementById('info-modal'),
    btnInfo: document.getElementById('btn-info'),
    btnCloseInfo: document.getElementById('btn-close-info'),
    shareModal: document.getElementById('share-modal'),
    btnCloseShare: document.getElementById('btn-close-share'),
    shareLink: document.getElementById('share-link'),
    btnCopyLink: document.getElementById('btn-copy-link'),
    setupModal: document.getElementById('setup-modal'),
    btnSetup: document.getElementById('btn-setup'),
    btnCloseSetup: document.getElementById('btn-close-setup')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    checkServerStatus();
    handleUrlParams();
    loadSettings();
});

// Event Listeners
function initEventListeners() {
    // Voice file upload
    elements.voiceFile.addEventListener('change', handleFileUpload);
    elements.btnRecord.addEventListener('click', toggleRecording);
    elements.btnClearAudio.addEventListener('click', clearVoice);
    
    // Text input tabs
    elements.textTabBtns.forEach(btn => {
        btn.addEventListener('click', () => switchTextTab(btn.dataset.tab));
    });
    
    // Text input
    elements.textInput.addEventListener('input', updateCharCount);
    elements.btnFetchUrl.addEventListener('click', fetchUrlContent);
    
    // Settings
    elements.speedSlider.addEventListener('input', updateSpeedValue);
    
    // Generate
    elements.btnGenerate.addEventListener('click', generateSpeech);
    
    // Output actions
    elements.btnDownload.addEventListener('click', downloadAudio);
    elements.btnShare.addEventListener('click', showShareModal);
    
    // Settings panel
    elements.btnToggleSettings.addEventListener('click', toggleSettings);
    elements.serverUrlInput.addEventListener('change', updateServerUrl);
    
    // Modals
    elements.btnInfo.addEventListener('click', () => showModal('info-modal'));
    elements.btnCloseInfo.addEventListener('click', () => hideModal('info-modal'));
    elements.btnCloseShare.addEventListener('click', () => hideModal('share-modal'));
    elements.btnCopyLink.addEventListener('click', copyShareLink);
    elements.btnSetup.addEventListener('click', () => showModal('setup-modal'));
    elements.btnCloseSetup.addEventListener('click', () => hideModal('setup-modal'));
    
    // Local setup modal
    const btnLocalHelp = document.getElementById('btn-local-help');
    const btnCloseLocal = document.getElementById('btn-close-local');
    if (btnLocalHelp) {
        btnLocalHelp.addEventListener('click', () => showModal('local-modal'));
    }
    if (btnCloseLocal) {
        btnCloseLocal.addEventListener('click', () => hideModal('local-modal'));
    }
    
    // OS tab switching in local modal
    document.querySelectorAll('.os-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const os = btn.dataset.os;
            // Update buttons
            document.querySelectorAll('.os-tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Update panels
            document.querySelectorAll('.os-panel').forEach(p => p.classList.remove('active'));
            document.querySelector(`.os-panel[data-os="${os}"]`)?.classList.add('active');
        });
    });
    
    // Save settings checkbox
    const saveSettingsCheckbox = document.getElementById('save-settings');
    if (saveSettingsCheckbox) {
        saveSettingsCheckbox.addEventListener('change', () => {
            if (saveSettingsCheckbox.checked) {
                saveSettings();
            } else {
                localStorage.removeItem('My Voice_settings');
            }
        });
    }
    
    // Copy code buttons in setup modal and local modal
    document.querySelectorAll('.btn-copy-code').forEach(btn => {
        btn.addEventListener('click', () => {
            // Try data-target first, then find adjacent pre
            const targetId = btn.dataset.target;
            let code;
            if (targetId) {
                code = document.getElementById(targetId)?.textContent;
            }
            if (!code) {
                // Find pre in same .code-block container
                const codeBlock = btn.closest('.code-block');
                const pre = codeBlock?.querySelector('pre');
                code = pre?.textContent;
            }
            if (code) {
                navigator.clipboard.writeText(code.trim()).then(() => {
                    const originalText = btn.textContent;
                    btn.textContent = 'Copied!';
                    setTimeout(() => btn.textContent = originalText, 2000);
                });
            }
        });
    });
    
    // Close modals on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.add('hidden');
            }
        });
    });
    
    // Update generate button state
    elements.textInput.addEventListener('input', updateGenerateButton);
}

// Voice File Handling
function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    elements.fileName.textContent = file.name;
    state.voiceFileName = file.name;
    
    const reader = new FileReader();
    reader.onload = (event) => {
        state.voiceData = event.target.result;
        showAudioPreview(state.voiceData);
        updateGenerateButton();
    };
    reader.readAsDataURL(file);
}

function showAudioPreview(audioData) {
    elements.voiceAudio.src = audioData;
    elements.audioPreview.classList.remove('hidden');
}

function clearVoice() {
    state.voiceData = null;
    state.voiceFileName = null;
    elements.voiceFile.value = '';
    elements.fileName.textContent = 'No file selected';
    elements.audioPreview.classList.add('hidden');
    elements.voiceAudio.src = '';
    elements.recordStatus.textContent = '';
    updateGenerateButton();
}

// Recording
async function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.mediaRecorder = new MediaRecorder(stream);
        state.audioChunks = [];
        
        state.mediaRecorder.ondataavailable = (e) => {
            state.audioChunks.push(e.data);
        };
        
        state.mediaRecorder.onstop = () => {
            const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
            const reader = new FileReader();
            reader.onload = (event) => {
                state.voiceData = event.target.result;
                state.voiceFileName = 'recorded_voice.webm';
                showAudioPreview(state.voiceData);
                updateGenerateButton();
            };
            reader.readAsDataURL(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        state.mediaRecorder.start();
        state.isRecording = true;
        
        elements.btnRecord.classList.add('recording');
        elements.recordIcon.classList.add('hidden');
        elements.stopIcon.classList.remove('hidden');
        elements.recordText.textContent = 'Stop Recording';
        elements.recordStatus.textContent = 'Recording...';
        
    } catch (err) {
        console.error('Recording error:', err);
        elements.recordStatus.textContent = 'Error: Could not access microphone';
    }
}

function stopRecording() {
    if (state.mediaRecorder && state.isRecording) {
        state.mediaRecorder.stop();
        state.isRecording = false;
        
        elements.btnRecord.classList.remove('recording');
        elements.recordIcon.classList.remove('hidden');
        elements.stopIcon.classList.add('hidden');
        elements.recordText.textContent = 'Record Voice';
        elements.recordStatus.textContent = 'Recording saved';
    }
}

// Text Input
function switchTextTab(tab) {
    elements.textTabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    
    elements.textPanel.classList.toggle('active', tab === 'text');
    elements.urlPanel.classList.toggle('active', tab === 'url');
}

function updateCharCount() {
    const count = elements.textInput.value.length;
    elements.charCount.textContent = count;
}

// Client-side URL fetching (using CORS proxies - same as whodoneit)
async function fetchWithProxy(url) {
    // First try direct fetch (works for CORS-enabled sites)
    try {
        const directResp = await fetch(url, {
            headers: { 'Accept': 'text/html' }
        });
        if (directResp.ok) {
            return await directResp.text();
        }
    } catch (e) {
        // Expected CORS error, continue to proxies
    }

    // Try CORS proxies
    for (const proxy of CORS_PROXIES) {
        try {
            const proxyUrl = proxy + encodeURIComponent(url);
            const resp = await fetch(proxyUrl);
            if (resp.ok) {
                return await resp.text();
            }
        } catch (e) {
            // Continue to next proxy
        }
    }

    throw new Error('Could not fetch URL. The site may be blocking automated requests.');
}

/**
 * Extract main text content from HTML (based on whodoneit implementation)
 */
function extractContent(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    // Remove script, style, nav, header, footer, aside, comments
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

    // Try to find main content using common patterns
    const contentSelectors = [
        // Specific blog platforms
        'article.post-content',
        'article .post-content',
        '.post-content',
        '.entry-content',
        '.article-content',
        '.content-body',
        '.blog-post-content',
        '.single-post-content',
        
        // Substack specific
        '.body.markup',
        '.post-content-final',
        '[data-component-name="BodyMarkup"]',
        
        // Medium-like
        'article section',
        
        // Generic semantic
        'article',
        '[role="main"]',
        'main',
        '.main-content',
        '#main-content',
        '.content',
        '#content',
        
        // Fallback to body
        'body'
    ];

    let contentEl = null;
    for (const selector of contentSelectors) {
        const el = doc.querySelector(selector);
        if (el) {
            const text = el.textContent.trim();
            // Accept if it has substantial content (at least 200 chars)
            if (text.length > 200) {
                contentEl = el;
                break;
            }
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
                // Add heading markers
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
        // Fallback: get all text
        blocks.push(contentEl.textContent.trim());
    }

    // Join with double newlines for paragraph separation
    let content = blocks.join('\n\n');

    // Clean up excessive whitespace
    content = content
        .replace(/\n{3,}/g, '\n\n')
        .replace(/[ \t]+/g, ' ')
        .trim();

    return content;
}

async function fetchUrlContent() {
    const url = elements.urlInput.value.trim();
    if (!url) {
        elements.urlStatus.textContent = 'Please enter a URL';
        elements.urlStatus.className = 'url-status error';
        return;
    }
    
    // Validate URL
    try {
        new URL(url);
    } catch {
        elements.urlStatus.textContent = 'Please enter a valid URL';
        elements.urlStatus.className = 'url-status error';
        return;
    }
    
    elements.urlStatus.textContent = 'Fetching...';
    elements.urlStatus.className = 'url-status';
    elements.btnFetchUrl.disabled = true;
    if (elements.fetchText) elements.fetchText.textContent = 'Fetching...';
    
    try {
        const html = await fetchWithProxy(url);
        
        if (!html || html.length < 100) {
            throw new Error('Could not retrieve content from this URL.');
        }
        
        const text = extractContent(html);
        
        if (!text || text.length < 50) {
            throw new Error('Could not extract meaningful content. The site may use JavaScript rendering.');
        }
        
        elements.textInput.value = text;
        updateCharCount();
        switchTextTab('text');
        
        elements.urlStatus.textContent = `Fetched ${text.length.toLocaleString()} characters`;
        elements.urlStatus.className = 'url-status success';
        updateGenerateButton();
        
        // Clear URL input after successful fetch
        elements.urlInput.value = '';
        
        // Focus on text input
        elements.textInput.focus();
        
    } catch (err) {
        console.error('Fetch error:', err);
        elements.urlStatus.textContent = err.message || 'Error fetching URL';
        elements.urlStatus.className = 'url-status error';
    } finally {
        elements.btnFetchUrl.disabled = false;
        if (elements.fetchText) elements.fetchText.textContent = 'Fetch';
    }
}

// Generate Speech using local TTS server
async function generateSpeech() {
    if (!state.voiceData || !elements.textInput.value.trim()) {
        return;
    }
    
    // Preflight check
    const preflight = await preflightCheck();
    if (!preflight.ok) {
        updateProgress(0, preflight.error);
        return;
    }
    
    setGenerating(true);
    updateProgress(5, 'Connecting to server...');
    
    try {
        const text = elements.textInput.value.trim();
        const language = elements.languageSelect.value;
        const speed = parseFloat(elements.speedSlider.value);
        
        // Estimate chunks and time
        const estimatedChunks = Math.ceil(text.length / 200);
        const isLongText = text.length > 500;
        const gpuAvailable = preflight.gpu;
        
        let progressMsg = 'Sending to TTS server...';
        if (isLongText && !gpuAvailable) {
            progressMsg = `Processing ${estimatedChunks} chunks (CPU mode ~${estimatedChunks * 15}s)...`;
        }
        updateProgress(10, progressMsg);
        
        // Call local /api/tts endpoint
        const response = await fetch(`${state.serverUrl}/api/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                voice: state.voiceData,
                language: language,
                speed: speed
            })
        });
        
        // Show progress while waiting for response
        let progressValue = 15;
        const progressInterval = setInterval(() => {
            if (progressValue < 85) {
                progressValue += isLongText ? 1 : 3;
                const timeHint = isLongText && !gpuAvailable 
                    ? ' (GPU recommended for long text)' 
                    : '';
                updateProgress(progressValue, `Generating speech...${timeHint}`);
            }
        }, isLongText ? 2000 : 500);
        
        if (!response.ok) {
            clearInterval(progressInterval);
            const errorData = await response.json().catch(() => null);
            const errorMsg = errorData?.error || `Server error: ${response.status}`;
            throw new Error(errorMsg);
        }
        
        clearInterval(progressInterval);
        updateProgress(90, 'Loading audio...');
        
        // Response is the audio file directly
        const audioBlob = await response.blob();
        state.generatedAudio = URL.createObjectURL(audioBlob);
        
        updateProgress(100, 'Complete!');
        showOutput();
        
    } catch (err) {
        console.error('Generation error:', err);
        
        if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
            updateProgress(0, 'Cannot connect to server. Make sure the TTS server is running.');
            elements.progressText.innerHTML = 'Cannot connect to server. <button onclick="document.getElementById(\'local-modal\').classList.remove(\'hidden\')" style="text-decoration:underline;background:none;border:none;color:inherit;cursor:pointer;">Setup Instructions</button>';
        } else {
            updateProgress(0, `Error: ${err.message}`);
        }
    } finally {
        setTimeout(() => {
            setGenerating(false);
        }, 1000);
    }
}

// Preflight check to verify server is running
async function preflightCheck() {
    const base = state.serverUrl.replace(/\/+$/, '');
    
    try {
        const response = await fetch(`${base}/api/health`, { 
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        
        if (!response.ok) {
            return {
                ok: false,
                error: 'Server not responding correctly. Check the URL.'
            };
        }
        
        const data = await response.json();
        
        if (!data.model_loaded && data.model_loaded !== undefined) {
            return {
                ok: false,
                error: 'TTS model not loaded. Wait for server to finish loading.'
            };
        }
        
        return { ok: true, status: data, gpu: data.cuda_available || false };
        
    } catch (err) {
        if (err.name === 'AbortError' || err.name === 'TimeoutError') {
            return {
                ok: false,
                error: 'Server not responding. Make sure the TTS server is running:\n\npython server.py'
            };
        }
        
        return {
            ok: false,
            error: 'Cannot connect to TTS server at ' + base + '.\n\n' +
                   'Start the server with: python server.py\n' +
                   'Click "Setup Instructions" in Settings for full guide.'
        };
    }
}

function setGenerating(isGenerating) {
    elements.btnGenerate.disabled = isGenerating;
    elements.generateIcon.classList.toggle('hidden', isGenerating);
    elements.generateText.textContent = isGenerating ? 'Generating...' : 'Generate Speech';
    elements.generateSpinner.classList.toggle('hidden', !isGenerating);
    elements.progressContainer.classList.toggle('hidden', !isGenerating);
    
    if (isGenerating) {
        updateProgress(0, 'Starting...');
    }
}

function updateProgress(percent, text) {
    elements.progressFill.style.width = `${percent}%`;
    elements.progressText.textContent = text;
}

function showOutput() {
    if (state.generatedAudio) {
        elements.outputAudio.src = state.generatedAudio;
        elements.outputSection.classList.remove('hidden');
        // Scroll to output
        elements.outputSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Output Actions
function downloadAudio() {
    if (!state.generatedAudio) return;
    
    const a = document.createElement('a');
    a.href = state.generatedAudio;
    a.download = 'My Voice_generated.wav';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function showShareModal() {
    const params = new URLSearchParams();
    params.set('text', elements.textInput.value);
    params.set('language', elements.languageSelect.value);
    params.set('speed', elements.speedSlider.value);
    
    const shareUrl = `${window.location.origin}${window.location.pathname}?${params.toString()}`;
    elements.shareLink.value = shareUrl;
    
    showModal('share-modal');
}

async function copyShareLink() {
    try {
        await navigator.clipboard.writeText(elements.shareLink.value);
        elements.btnCopyLink.textContent = 'Copied!';
        setTimeout(() => {
            elements.btnCopyLink.textContent = 'Copy';
        }, 2000);
    } catch (err) {
        console.error('Copy failed:', err);
    }
}

// Settings
function toggleSettings() {
    elements.settingsContent.classList.toggle('hidden');
}

function updateSpeedValue() {
    const value = parseFloat(elements.speedSlider.value).toFixed(1);
    elements.speedValue.textContent = `${value}x`;
    saveSettings();
}

function updateServerUrl() {
    state.serverUrl = elements.serverUrlInput.value.trim() || 'https://x97115104-myvoice.hf.space';
    saveSettings();
    checkServerStatus();
}

function loadSettings() {
    try {
        const saved = localStorage.getItem('My Voice_settings');
        if (saved) {
            const settings = JSON.parse(saved);
            elements.speedSlider.value = settings.speed || 1;
            elements.languageSelect.value = settings.language || 'en';
            elements.serverUrlInput.value = settings.serverUrl || 'https://x97115104-myvoice.hf.space';
            state.serverUrl = settings.serverUrl || 'https://x97115104-myvoice.hf.space';
            updateSpeedValue();
        }
    } catch (err) {
        console.error('Load settings error:', err);
    }
}

function saveSettings() {
    try {
        const settings = {
            speed: elements.speedSlider.value,
            language: elements.languageSelect.value,
            serverUrl: state.serverUrl
        };
        localStorage.setItem('My Voice_settings', JSON.stringify(settings));
    } catch (err) {
        console.error('Save settings error:', err);
    }
}

// Server Status
async function checkServerStatus() {
    elements.statusDot.className = 'status-dot checking';
    elements.statusText.textContent = 'Checking server...';
    
    try {
        // Try local TTS server /api/health endpoint
        const response = await fetch(`${state.serverUrl}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.model_loaded === false) {
                elements.statusDot.className = 'status-dot checking';
                elements.statusText.textContent = 'Model loading...';
            } else {
                elements.statusDot.className = 'status-dot online';
                elements.statusText.textContent = data.device === 'cuda' ? 'Server online (GPU)' : 'Server online (CPU)';
            }
        } else {
            throw new Error('Server error');
        }
    } catch (err) {
        elements.statusDot.className = 'status-dot offline';
        elements.statusText.textContent = 'Server offline';
    }
}

// URL Parameters
function handleUrlParams() {
    const params = new URLSearchParams(window.location.search);
    
    // Pre-fill text
    if (params.has('text')) {
        elements.textInput.value = decodeURIComponent(params.get('text'));
        updateCharCount();
    }
    
    // Fetch from URL
    if (params.has('url')) {
        elements.urlInput.value = decodeURIComponent(params.get('url'));
        switchTextTab('url');
        // Auto-fetch after a short delay
        setTimeout(fetchUrlContent, 500);
    }
    
    // Settings
    if (params.has('language')) {
        elements.languageSelect.value = params.get('language');
    }
    if (params.has('speed')) {
        elements.speedSlider.value = params.get('speed');
        updateSpeedValue();
    }
    
    updateGenerateButton();
}

// UI Helpers
function updateGenerateButton() {
    const hasVoice = !!state.voiceData;
    const hasText = elements.textInput.value.trim().length > 0;
    elements.btnGenerate.disabled = !(hasVoice && hasText);
}

function showModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
}

function hideModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

// Periodic server check
setInterval(checkServerStatus, 60000);
