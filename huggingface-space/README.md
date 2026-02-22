---
title: My Voice
emoji: 🎤
colorFrom: gray
colorTo: gray
sdk: gradio
sdk_version: "4.44.0"
python_version: "3.10"
app_file: app.py
pinned: false
license: mit
---

# My Voice - Voice Cloning TTS

Clone any voice and generate speech from text using XTTS v2.

## Features
- Voice cloning from short audio samples (10-30 seconds)
- Multi-language support (16+ languages)
- Adjustable speech speed
- Free GPU inference via Hugging Face Spaces

## API Usage

This Space exposes an API endpoint for programmatic access:

```bash
curl -X POST "https://x97115104-myvoice.hf.space/api/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "Hello, this is my cloned voice.",
      "data:audio/wav;base64,<base64_audio>",
      "en",
      1.0
    ]
  }'
```

## Credits
- [Coqui XTTS v2](https://github.com/coqui-ai/TTS)
- Created by [97 115 104](https://github.com/97115104)
