"""
My Voice - Voice Cloning & Text-to-Speech Server
A free, self-hosted voice cloning server using XTTS v2

Usage:
    python server.py [--port PORT] [--host HOST]
    
API Endpoints:
    GET  /api/health       - Check server status
    POST /api/tts          - Generate speech from text
    POST /api/fetch-url    - Extract text from URL
    GET  /api/generate     - Generate speech via URL params
"""

import os
import sys

# Accept Coqui TOS automatically - MUST be before TTS imports
os.environ["COQUI_TOS_AGREED"] = "1"

import json
import base64
import tempfile
import argparse
import logging
from pathlib import Path
from io import BytesIO
from urllib.parse import urlparse

# Flask for web server
from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS

# Audio processing
import torch
import torchaudio

# TTS - Coqui XTTS
from TTS.api import TTS

# URL content extraction
import requests
from bs4 import BeautifulSoup
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)

# Global TTS model and cache
tts_model = None
xtts_model = None  # Lower-level model for advanced control
speaker_cache = {}  # Cache speaker embeddings
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"


def load_model():
    """Load the XTTS v2 model"""
    global tts_model, xtts_model
    
    logger.info("Loading XTTS v2 model...")
    logger.info("This may take a few minutes on first run (downloading ~2GB model)")
    
    # Check for GPU - CUDA (NVIDIA) or MPS (Apple Silicon)
    if torch.cuda.is_available():
        device = "cuda"
        logger.info("Using NVIDIA GPU (CUDA)")
    elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
        # MPS available but XTTS has compatibility issues with MPS
        # Some operations aren't supported, falling back to CPU for reliability
        device = "cpu"
        logger.info("Apple Silicon detected - MPS available but using CPU for XTTS compatibility")
        logger.info("Note: XTTS v2 has limited MPS support. CPU is more reliable.")
    else:
        device = "cpu"
        logger.warning("Running on CPU - generation will be slow (~15-30s per sentence)")
        logger.warning("For faster generation on NVIDIA GPU:")
        logger.warning("  pip3 install torch torchaudio --index-url https://download.pytorch.org/whl/cu121")
    
    logger.info(f"Using device: {device}")
    
    try:
        tts_model = TTS(MODEL_NAME).to(device)
        # Access underlying XTTS model for advanced control
        xtts_model = tts_model.synthesizer.tts_model
        logger.info("Model loaded successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


def decode_audio_data(audio_data_url):
    """Decode base64 audio data URL to file"""
    # Remove data URL prefix
    if ',' in audio_data_url:
        header, data = audio_data_url.split(',', 1)
    else:
        data = audio_data_url
    
    # Decode base64
    audio_bytes = base64.b64decode(data)
    
    # Save to temp file
    suffix = '.wav'
    if 'audio/mp3' in audio_data_url or 'audio/mpeg' in audio_data_url:
        suffix = '.mp3'
    elif 'audio/m4a' in audio_data_url or 'audio/x-m4a' in audio_data_url:
        suffix = '.m4a'
    elif 'audio/webm' in audio_data_url:
        suffix = '.webm'
    elif 'audio/ogg' in audio_data_url:
        suffix = '.ogg'
    
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_file.write(audio_bytes)
    temp_file.close()
    
    return temp_file.name


def convert_to_wav(input_path):
    """Convert audio file to WAV format for XTTS"""
    output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    
    try:
        # Use pydub (ffmpeg) for robust format handling (m4a, mp3, webm, etc.)
        from pydub import AudioSegment
        
        # Detect format from extension
        ext = Path(input_path).suffix.lower().lstrip('.')
        if ext == 'm4a':
            ext = 'mp4'  # pydub uses mp4 for m4a
        elif ext in ['', 'wav']:
            ext = 'wav'
        
        # Load with pydub
        audio = AudioSegment.from_file(input_path, format=ext if ext else None)
        
        # Convert to mono, 22050 Hz
        audio = audio.set_channels(1).set_frame_rate(22050)
        
        # Export as WAV
        audio.export(output_path, format='wav')
        
        return output_path
    except Exception as e:
        logger.error(f"Audio conversion error with pydub: {e}")
        # Fallback to torchaudio
        try:
            waveform, sample_rate = torchaudio.load(input_path)
            
            # Convert to mono if stereo
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
            
            # Resample to 22050 Hz (XTTS requirement)
            if sample_rate != 22050:
                resampler = torchaudio.transforms.Resample(sample_rate, 22050)
                waveform = resampler(waveform)
            
            # Save as WAV
            torchaudio.save(output_path, waveform, 22050)
            
            return output_path
        except Exception as e2:
            logger.error(f"Fallback audio conversion error: {e2}")
            return input_path


def extract_text_from_url(url):
    """Extract readable text and title from a URL, preserving paragraph structure"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = ''
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        # Also try h1 if title is generic or missing
        h1_tag = soup.find('h1')
        if h1_tag:
            h1_text = h1_tag.get_text(strip=True)
            if not title or len(title) > 100 or '|' in title:
                title = h1_text
        
        # Remove unwanted elements
        remove_selectors = [
            'script', 'style', 'noscript', 'nav', 'header', 'footer', 
            'aside', 'iframe', 'form', 'button'
        ]
        for selector in remove_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Also remove by class/id patterns
        for pattern in ['.comments', '#comments', '.sidebar', '.navigation', '.menu', 
                        '.social-share', '.related-posts', '.advertisement', '.ad',
                        '.cookie-notice', '.popup', '.modal', '.newsletter', '.subscribe']:
            for element in soup.select(pattern):
                element.decompose()
        
        # Try to find main content
        content_selectors = [
            'article.post-content', 'article .post-content', '.post-content',
            '.entry-content', '.article-content', '.content-body', '.blog-post-content',
            '.body.markup', '.post-content-final', 'article', '[role="main"]',
            'main', '.main-content', '#main-content', '.content', '#content', 'body'
        ]
        
        main_content = None
        for selector in content_selectors:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > 200:
                main_content = el
                break
        
        if not main_content:
            main_content = soup.body or soup
        
        # Extract text, preserving paragraph structure
        blocks = []
        block_tags = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'pre'])
        
        if block_tags:
            for el in block_tags:
                text = el.get_text(strip=True)
                if text:
                    tag_name = el.name
                    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        blocks.append('\n' + text + '\n')
                    elif tag_name == 'blockquote':
                        blocks.append('> ' + text)
                    elif tag_name == 'pre':
                        blocks.append('```\n' + text + '\n```')
                    elif tag_name == 'li':
                        blocks.append('• ' + text)
                    else:
                        blocks.append(text)
        else:
            # Fallback: get all text
            blocks.append(main_content.get_text(strip=True))
        
        # Join with double newlines for paragraph separation
        content = '\n\n'.join(blocks)
        
        # Clean up excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = content.strip()
        
        return content, title
        
    except Exception as e:
        logger.error(f"URL extraction error: {e}")
        raise


def split_text_into_chunks(text, max_chars=300):
    """Split text into sentence chunks for XTTS processing.
    
    XTTS v2 works best with shorter text segments (under 400 chars).
    Using 300 chars for better prosody while staying safe.
    This function splits on sentence boundaries for natural speech.
    """
    # Split on sentence endings
    sentence_endings = re.compile(r'(?<=[.!?])\s+')
    sentences = sentence_endings.split(text)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # If sentence itself is too long, split on commas/semicolons
        if len(sentence) > max_chars:
            # Split on clause boundaries
            clause_split = re.split(r'(?<=[,;:])\s+', sentence)
            for clause in clause_split:
                clause = clause.strip()
                if not clause:
                    continue
                if len(current_chunk) + len(clause) + 1 <= max_chars:
                    current_chunk = f"{current_chunk} {clause}".strip()
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    # If clause is still too long, force split
                    if len(clause) > max_chars:
                        words = clause.split()
                        current_chunk = ""
                        for word in words:
                            if len(current_chunk) + len(word) + 1 <= max_chars:
                                current_chunk = f"{current_chunk} {word}".strip()
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk)
                                current_chunk = word
                    else:
                        current_chunk = clause
        elif len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk = f"{current_chunk} {sentence}".strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def concatenate_audio_files(audio_paths, output_path, crossfade_ms=50):
    """Concatenate multiple audio files with crossfade for smoother transitions"""
    from pydub import AudioSegment
    
    if not audio_paths:
        return None
    
    # Start with first audio
    combined = AudioSegment.from_wav(audio_paths[0])
    
    # Add remaining with crossfade
    for path in audio_paths[1:]:
        try:
            audio = AudioSegment.from_wav(path)
            # Use crossfade for smoother transitions between chunks
            if crossfade_ms > 0 and len(combined) > crossfade_ms and len(audio) > crossfade_ms:
                combined = combined.append(audio, crossfade=crossfade_ms)
            else:
                # Fallback: small silence between chunks
                combined += AudioSegment.silent(duration=100) + audio
        except Exception as e:
            logger.warning(f"Failed to load audio chunk {path}: {e}")
            continue
    
    # Export combined audio
    combined.export(output_path, format='wav')
    return output_path


def get_speaker_embedding(wav_path, cache_key=None):
    """Get speaker embedding from audio file, with optional caching"""
    global speaker_cache, xtts_model
    
    if cache_key and cache_key in speaker_cache:
        logger.info(f"Using cached speaker embedding")
        return speaker_cache[cache_key]
    
    if xtts_model is None:
        return None, None
    
    # Generate speaker embedding using XTTS
    gpt_cond_latent, speaker_embedding = xtts_model.get_conditioning_latents(
        audio_path=wav_path
    )
    
    if cache_key:
        speaker_cache[cache_key] = (gpt_cond_latent, speaker_embedding)
        logger.info(f"Cached speaker embedding for future use")
    
    return gpt_cond_latent, speaker_embedding


# API Routes

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check server health and model status"""
    return jsonify({
        'status': 'ok',
        'model': 'XTTS v2',
        'model_loaded': tts_model is not None,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'cuda_available': torch.cuda.is_available()
    })


@app.route('/api/tags', methods=['GET'])
def api_tags():
    """Ollama-compatible tags endpoint for preflight checks"""
    return jsonify({
        'models': [
            {'name': 'xtts_v2', 'size': '1.8GB'}
        ]
    })


@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """Generate speech from text using cloned voice
    
    Request body:
    {
        "text": "Text to speak",
        "voice": "base64 audio data URL",
        "language": "en",
        "speed": 1.0
    }
    """
    if tts_model is None:
        return jsonify({'error': 'Model not loaded'}), 503
    
    try:
        data = request.get_json()
        
        text = data.get('text', '').strip()
        voice_data = data.get('voice')
        language = data.get('language', 'en')
        speed = float(data.get('speed', 1.0))
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if not voice_data:
            return jsonify({'error': 'No voice sample provided'}), 400
        
        logger.info(f"Generating speech: {len(text)} chars, lang={language}, speed={speed}")
        
        # Decode and convert voice sample
        voice_path = decode_audio_data(voice_data)
        wav_path = convert_to_wav(voice_path)
        
        # Split text into chunks for reliable generation
        chunks = split_text_into_chunks(text, max_chars=200)
        total_chunks = len(chunks)
        logger.info(f"Split into {total_chunks} chunks for processing")
        
        if total_chunks > 10 and not torch.cuda.is_available():
            logger.warning("Long text on CPU - generation may take several minutes. Consider using GPU for faster processing.")
        
        # Generate audio for each chunk
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{total_chunks}: {len(chunk)} chars")
            
            chunk_output = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            
            try:
                tts_model.tts_to_file(
                    text=chunk,
                    speaker_wav=wav_path,
                    language=language,
                    file_path=chunk_output,
                    speed=speed
                )
                chunk_paths.append(chunk_output)
            except Exception as e:
                logger.error(f"Failed to generate chunk {i+1}: {e}")
                # Continue with other chunks
                continue
        
        if not chunk_paths:
            return jsonify({'error': 'Failed to generate any audio chunks'}), 500
        
        # Concatenate all chunks
        if len(chunk_paths) == 1:
            output_path = chunk_paths[0]
        else:
            output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            concatenate_audio_files(chunk_paths, output_path)
            # Clean up individual chunk files
            for path in chunk_paths:
                try:
                    os.unlink(path)
                except:
                    pass
        
        # Convert to MP3 for smaller file size
        mp3_path = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
        
        from pydub import AudioSegment
        audio = AudioSegment.from_wav(output_path)
        audio.export(mp3_path, format='mp3', bitrate='192k')
        
        # Clean up temp files
        try:
            os.unlink(voice_path)
            os.unlink(wav_path)
            os.unlink(output_path)
        except:
            pass
        
        logger.info("Speech generation complete")
        
        # Return audio file
        return send_file(
            mp3_path,
            mimetype='audio/mpeg',
            as_attachment=False,
            download_name='generated.mp3'
        )
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate', methods=['GET'])
def generate_via_url():
    """Generate speech via URL parameters
    
    Query parameters:
        text: Text to speak
        voice_url: URL to voice sample
        voice_file: Path to local voice file
        language: Language code (default: en)
        speed: Speed multiplier (default: 1.0)
    """
    if tts_model is None:
        return jsonify({'error': 'Model not loaded'}), 503
    
    try:
        text = request.args.get('text', '').strip()
        voice_url = request.args.get('voice_url')
        voice_file = request.args.get('voice_file')
        language = request.args.get('language', 'en')
        speed = float(request.args.get('speed', 1.0))
        
        if not text:
            return jsonify({'error': 'No text provided. Use ?text=your text here'}), 400
        
        # Get voice sample
        if voice_url:
            # Download voice from URL
            response = requests.get(voice_url, timeout=30)
            response.raise_for_status()
            
            voice_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            with open(voice_path, 'wb') as f:
                f.write(response.content)
        elif voice_file:
            voice_path = voice_file
            if not os.path.exists(voice_path):
                # Check in assets/examples
                alt_path = os.path.join(os.path.dirname(__file__), 'assets', 'examples', voice_file)
                if os.path.exists(alt_path):
                    voice_path = alt_path
                else:
                    return jsonify({'error': f'Voice file not found: {voice_file}'}), 400
        else:
            # Use default example voice
            default_voice = os.path.join(os.path.dirname(__file__), 'assets', 'examples', 'my voice.m4a')
            if os.path.exists(default_voice):
                voice_path = default_voice
            else:
                return jsonify({'error': 'No voice sample provided'}), 400
        
        logger.info(f"URL generation: {len(text)} chars, lang={language}, speed={speed}")
        
        # Convert voice to WAV
        wav_path = convert_to_wav(voice_path)
        
        # Generate speech
        output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        tts_model.tts_to_file(
            text=text,
            speaker_wav=wav_path,
            language=language,
            file_path=output_path,
            speed=speed
        )
        
        # Convert to MP3
        mp3_path = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
        waveform, sample_rate = torchaudio.load(output_path)
        torchaudio.save(mp3_path, waveform, sample_rate, format='mp3')
        
        # Clean up
        try:
            if voice_url:
                os.unlink(voice_path)
            os.unlink(wav_path)
            os.unlink(output_path)
        except:
            pass
        
        logger.info("URL generation complete")
        
        return send_file(
            mp3_path,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='generated.mp3'
        )
        
    except Exception as e:
        logger.error(f"URL generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/fetch-url', methods=['POST'])
def fetch_url():
    """Extract text content from a URL
    
    Request body:
    {
        "url": "https://example.com/article"
    }
    """
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return jsonify({'error': 'Invalid URL'}), 400
        
        text, title = extract_text_from_url(url)
        
        # Limit text length
        if len(text) > 50000:
            text = text[:50000] + '...'
        
        return jsonify({
            'text': text,
            'title': title,
            'url': url,
            'length': len(text)
        })
        
    except Exception as e:
        logger.error(f"URL fetch error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """Ollama-style status page"""
    return "My Voice is running", 200, {'Content-Type': 'text/plain'}


@app.route('/ui', methods=['GET'])
def serve_ui():
    """Serve the frontend UI"""
    return send_file('index.html')


@app.route('/batch', methods=['GET'])
def serve_batch():
    """Serve the batch generation UI"""
    return send_file('batch.html')


@app.route('/api/batch-tts', methods=['POST'])
def batch_text_to_speech():
    """Generate speech and save to specified path
    
    Request: multipart/form-data with:
    - voice: audio file
    - text: text to speak
    - language: language code
    - speed: speech speed
    - output_path: where to save the file
    """
    if tts_model is None:
        return jsonify({'error': 'Model not loaded'}), 503
    
    try:
        # Get form data
        text = request.form.get('text', '').strip()
        language = request.form.get('language', 'en')
        speed = float(request.form.get('speed', 1.0))
        output_path = request.form.get('output_path', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if not output_path:
            return jsonify({'error': 'No output path provided'}), 400
        
        # Get voice file
        if 'voice' not in request.files:
            return jsonify({'error': 'No voice file provided'}), 400
        
        voice_file = request.files['voice']
        
        # Preserve original file extension for format detection
        original_filename = voice_file.filename or 'voice.wav'
        ext = Path(original_filename).suffix or '.wav'
        
        # Save voice to temp file with correct extension
        voice_path = tempfile.NamedTemporaryFile(suffix=ext, delete=False).name
        voice_file.save(voice_path)
        
        logger.info(f"Voice file saved: {voice_path} (from {original_filename})")
        
        # Convert to WAV if needed
        wav_path = convert_to_wav(voice_path)
        
        logger.info(f"Batch TTS: {len(text)} chars, saving to {output_path}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Split text into chunks
        chunks = split_text_into_chunks(text, max_chars=200)
        total_chunks = len(chunks)
        logger.info(f"Split into {total_chunks} chunks for processing")
        
        # Generate audio for each chunk
        chunk_paths = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{total_chunks}")
            
            chunk_output = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
            
            try:
                tts_model.tts_to_file(
                    text=chunk,
                    speaker_wav=wav_path,
                    language=language,
                    file_path=chunk_output,
                    speed=speed
                )
                chunk_paths.append(chunk_output)
            except Exception as e:
                logger.error(f"Failed to generate chunk {i+1}: {e}")
                continue
        
        if not chunk_paths:
            return jsonify({'error': 'Failed to generate any audio'}), 500
        
        # Concatenate all chunks
        if len(chunk_paths) == 1:
            # Just copy the single chunk to output
            import shutil
            shutil.copy(chunk_paths[0], output_path)
        else:
            concatenate_audio_files(chunk_paths, output_path)
        
        # Clean up temp files
        for path in chunk_paths:
            try:
                os.unlink(path)
            except:
                pass
        try:
            os.unlink(voice_path)
            if wav_path != voice_path:
                os.unlink(wav_path)
        except:
            pass
        
        logger.info(f"Batch TTS complete: {output_path}")
        
        return jsonify({
            'success': True,
            'output_path': output_path,
            'chunks': total_chunks
        })
        
    except Exception as e:
        logger.error(f"Batch TTS error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/css/<path:filename>')
def serve_css(filename):
    """Serve CSS files"""
    return send_file(f'css/{filename}')


@app.route('/js/<path:filename>')
def serve_js(filename):
    """Serve JS files"""
    return send_file(f'js/{filename}')


def main():
    parser = argparse.ArgumentParser(description='My Voice TTS Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5123, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    # Load model
    if not load_model():
        logger.error("Failed to load TTS model. Please check your installation.")
        sys.exit(1)
    
    logger.info(f"Starting server on http://{args.host}:{args.port}")
    logger.info("Press Ctrl+C to stop")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )


if __name__ == '__main__':
    main()
