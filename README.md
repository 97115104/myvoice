# My Voice

Clone any voice and generate natural-sounding speech from text.

**[Try it now →](https://97115104.github.io/myvoice/)**

## What it does

My Voice lets you clone any voice from a short audio sample and generate speech from text. Upload 10-30 seconds of someone speaking, enter your text, and get natural-sounding audio in their voice.

## Features

- **Voice Cloning** - Clone any voice from a short audio sample
- **Text-to-Speech** - Convert text into speech using the cloned voice
- **Multi-language Support** - 16+ languages including English, Spanish, French, German, Chinese, Japanese
- **URL Content Extraction** - Fetch article text directly from URLs
- **Browser Recording** - Record voice samples directly in the browser
- **Free** - Uses Hugging Face Spaces for free GPU inference

## How to use

1. **Provide a voice sample** - Upload an audio file (MP3, M4A, WAV) or record directly in the browser. 10-30 seconds of clear speech works best.
2. **Enter your text** - Type the text you want to convert, or fetch content from a URL.
3. **Generate** - Click generate and wait for the AI to synthesize your audio (~10-30 seconds).
4. **Download** - Download the audio file or share a link.

## URL Parameters

Pre-fill the UI via URL parameters for easy sharing:

```
?text=Hello%20world           # Pre-fill text
?url=https://example.com      # Fetch text from URL
?language=es                  # Set language (en, es, fr, de, etc.)
?speed=1.2                    # Set speech speed
```

**Example:** [Listen to a blog post](https://97115104.github.io/myvoice/?url=https://97115104.com/2026/02/19/fetch-quests/)

## Supported Languages

English, Spanish, French, German, Italian, Portuguese, Polish, Turkish, Russian, Dutch, Czech, Arabic, Chinese, Japanese, Korean, Hindi

## Tips for best results

- **Clear samples**: Use audio with minimal background noise
- **Right length**: 10-30 seconds of continuous speech
- **Match languages**: Best quality when sample language matches output language
- **WAV format**: Tends to produce best quality

## Privacy

- Voice samples are processed on Hugging Face Spaces and deleted after generation
- Text is processed server-side and not logged
- URL fetching uses public CORS proxies

## Technical details

- **Model**: [XTTS v2](https://huggingface.co/coqui/XTTS-v2) by Coqui AI
- **Backend**: Gradio on [Hugging Face Spaces](https://huggingface.co/spaces/x97115104/myvoice) (free T4 GPU)
- **Frontend**: Static site on GitHub Pages
- **API**: https://x97115104-myvoice.hf.space

## Host your own

Want to run your own instance? See the [setup instructions](https://97115104.github.io/myvoice/) (click "Host your own").

## License

[MIT](LICENSE)

---

Created by [97 115 104](https://github.com/sponsors/97115104) · [View source](https://github.com/97115104/myvoice) · [Other projects](https://97115104.com/projects/)
