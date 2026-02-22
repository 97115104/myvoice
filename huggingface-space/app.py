import os
os.environ["COQUI_TOS_AGREED"] = "1"

import torch
import tempfile
import gradio as gr
import spaces
from TTS.api import TTS

# Try to import pydub for audio conversion
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

# Load model on CPU initially - ZeroGPU will provide GPU on-demand
print("Loading XTTS v2...")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
print("Model loaded!")

LANGUAGES = ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "ko", "hi"]


def convert_to_wav(audio_path):
    """Convert audio to WAV format if needed"""
    if not HAS_PYDUB:
        return audio_path
    
    if audio_path.lower().endswith('.wav'):
        return audio_path
    
    try:
        # Convert to WAV
        audio = AudioSegment.from_file(audio_path)
        wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        audio.export(wav_path, format="wav")
        return wav_path
    except Exception as e:
        print(f"Audio conversion warning: {e}")
        return audio_path


@spaces.GPU(duration=120)  # ZeroGPU: request GPU for up to 120 seconds
def generate(text, speaker_audio, language, speed):
    print(f"[DEBUG] generate called with: text={text[:50] if text else None}..., speaker_audio={speaker_audio}, language={language}, speed={speed}")
    
    if not text:
        return None
    
    if not speaker_audio:
        return None
    
    try:
        # Move model to GPU for inference
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tts.to(device)
        print(f"[DEBUG] Model on device: {device}")
        
        print(f"[DEBUG] Checking if file exists: {speaker_audio}")
        if not os.path.exists(speaker_audio):
            print(f"[ERROR] Audio file not found: {speaker_audio}")
            return None
        
        file_size = os.path.getsize(speaker_audio)
        print(f"[DEBUG] File size: {file_size} bytes")
        
        if file_size < 1000:
            print(f"[ERROR] Audio file too small: {file_size} bytes")
            return None
        
        # Convert audio if needed
        wav_audio = convert_to_wav(speaker_audio)
        print(f"[DEBUG] Using audio: {wav_audio}")
        
        output_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        print(f"[DEBUG] Generating TTS to: {output_path}")
        
        tts.tts_to_file(
            text=text,
            speaker_wav=wav_audio,
            language=language,
            speed=speed,
            file_path=output_path
        )
        
        print(f"[DEBUG] Generated audio: {output_path}, size: {os.path.getsize(output_path)} bytes")
        return output_path
    except Exception as e:
        print(f"[ERROR] TTS generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


# Use gr.Interface instead of gr.Blocks to avoid schema issues
demo = gr.Interface(
    fn=generate,
    inputs=[
        gr.Textbox(label="Text to speak", lines=3),
        gr.Audio(label="Voice Sample (10-30 sec)", type="filepath"),
        gr.Dropdown(label="Language", choices=LANGUAGES, value="en"),
        gr.Slider(label="Speed", minimum=0.5, maximum=2.0, value=1.0, step=0.1),
    ],
    outputs=gr.Audio(label="Generated Speech"),
    title="My Voice - Voice Cloning TTS",
    description="Clone any voice and generate speech. Upload 10-30 seconds of clear speech. Uses ZeroGPU for free GPU inference.",
    allow_flagging="never",
)

# Enable queue for ZeroGPU
demo.queue()
demo.launch()
