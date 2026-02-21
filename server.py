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

# Global TTS model
tts_model = None
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"


def load_model():
    """Load the XTTS v2 model"""
    global tts_model
    
    logger.info("Loading XTTS v2 model...")
    logger.info("This may take a few minutes on first run (downloading ~2GB model)")
    
    # Check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    
    try:
        tts_model = TTS(MODEL_NAME).to(device)
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
        # Load audio using torchaudio
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
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        # Try using the original file
        return input_path


def extract_text_from_url(url):
    """Extract readable text from a URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Try to find main content
        main_content = soup.find('article') or soup.find('main') or soup.find('body')
        
        if main_content:
            # Get text and clean it
            text = main_content.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
        
        return soup.get_text(separator=' ', strip=True)
        
    except Exception as e:
        logger.error(f"URL extraction error: {e}")
        raise


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
        
        # Generate speech
        output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        tts_model.tts_to_file(
            text=text,
            speaker_wav=wav_path,
            language=language,
            file_path=output_path,
            speed=speed
        )
        
        # Convert to MP3 for smaller file size
        mp3_path = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
        
        waveform, sample_rate = torchaudio.load(output_path)
        torchaudio.save(mp3_path, waveform, sample_rate, format='mp3')
        
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
        
        text = extract_text_from_url(url)
        
        # Limit text length
        if len(text) > 10000:
            text = text[:10000] + '...'
        
        return jsonify({
            'text': text,
            'url': url,
            'length': len(text)
        })
        
    except Exception as e:
        logger.error(f"URL fetch error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    """Serve the frontend"""
    return send_file('index.html')


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
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
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
