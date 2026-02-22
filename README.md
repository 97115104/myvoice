# My Voice

Clone any voice and generate closer to natural-sounding speech from text. Runs locally on your machine and requires cloning.

## What it does

My Voice lets you clone any voice from a short audio sample and generate speech from text. Upload 10-30 seconds of someone speaking, enter your text, and get naturalish-sounding audio in their voice.

## Features

- **Voice Cloning** - Clone any voice from a short audio sample
- **Text-to-Speech** - Convert text into speech using the cloned voice
- **Batch Generation** - Process multiple URLs at once with bulk import
- **Multi-language Support** - 16+ languages including English, Spanish, French, German, Chinese, Japanese
- **URL Content Extraction** - Fetch article text directly from URLs with paragraph preservation
- **Browser Recording** - Record voice samples directly in the browser
- **100% Local** - All processing happens on your machine, nothing leaves your computer
- **GPU Acceleration** - Uses CUDA (NVIDIA) or MPS (MacOS) automatically when available for faster generation

## Quick Start

```bash
# Install ffmpeg and Python 3.11 (required)
brew install ffmpeg python@3.11  # macOS
# sudo apt install ffmpeg python3.11  # Linux
# choco install ffmpeg python311  # Windows

# Install Python dependencies
pip3 install TTS flask flask-cors pydub beautifulsoup4 requests

# Clone and run
git clone https://github.com/97115104/myvoice.git
cd myvoice
python3 server.py
```

First run downloads the XTTS model (~1.8GB). Server starts on `http://localhost:5123`.

Open the UI at `http://localhost:5123/ui`.

## How to use

### Single Generation
1. **Start the server** - Run `python3 server.py` to start the local TTS server
2. **Open the UI** - Go to `http://localhost:5123/ui` in your browser
3. **Provide a voice sample** - Upload an audio file (MP3, M4A, WAV) or record directly in the browser. 10-30 seconds of clear speech works best.
4. **Enter your text** - Type the text you want to convert, or fetch content from a URL.
5. **Generate** - Click generate and wait for the AI to synthesize your audio.
6. **Download** - Download the audio file.

### Batch Generation
1. **Open the batch page** - Go to `http://localhost:5123/batch` in your browser
2. **Upload a voice sample** - Same as single generation
3. **Add URLs** - Either add URLs one at a time with "Preview & Add", or use "Bulk Import" to paste multiple URLs at once (one per line)
4. **Set output directory** - Choose where to save the generated files
5. **Generate All** - Click to process all queued items sequentially

## Requirements

- **Python 3.9-3.11** (TTS package doesn't support Python 3.12+)
- **ffmpeg** - For audio conversion (`brew install ffmpeg` on macOS)
- **~4GB disk space** - For the XTTS model
- **GPU (optional)** - CUDA GPU speeds up generation significantly

## Supported Languages

English, Spanish, French, German, Italian, Portuguese, Polish, Turkish, Russian, Dutch, Czech, Arabic, Chinese, Japanese, Korean, Hindi

## Tips for best results

- **Clear samples**: Use audio with minimal background noise
- **Right length**: 10-30 seconds of continuous speech
- **Match languages**: Best quality when sample language matches output language
- **WAV format**: Tends to produce best quality

## Privacy

Everything runs locally on your machine which means voice samples are processed locally and never uploaded, text processing happens on your computer and there is no telemetry or API calls to external services.

## Technical details

- **Model**: [XTTS v2](https://huggingface.co/coqui/XTTS-v2) by Coqui AI (~1.8GB)
- **Backend**: Flask server running on localhost:5123
- **Frontend**: Static HTML/CSS/JS

## GPU Acceleration (Windows/Linux with NVIDIA GPU)

For faster generation on **NVIDIA GPUs**, install CUDA PyTorch:

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

> **macOS users**: Apple Silicon (M1/M2/M3/M4) doesn't support CUDA - that's NVIDIA-only. XTTS will run on CPU. Generation takes ~15-30 seconds per chunk but works reliably.

## API Reference

The server exposes these endpoints:

```
GET  /api/health              # Server status check
POST /api/tts                 # Generate speech (form data: text, voice, language, speed)
POST /api/batch-tts           # Batch generate speech with file saving
POST /api/fetch-url           # Extract text from URL (preserves paragraphs)
GET  /api/tags                # Ollama-compatible model list
```

## License

[MIT](LICENSE)

---

Created by [97 115 104](https://github.com/sponsors/97115104) · [View source](https://github.com/97115104/myvoice) · [Other projects](https://97115104.com/projects/)
