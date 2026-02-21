"""
My Voice - Voice Cloning TTS API
Hugging Face Spaces Application

This Gradio app provides voice cloning text-to-speech via XTTS v2.
Deploy to Hugging Face Spaces for free GPU hosting.
"""

import os
import tempfile
import base64
import gradio as gr
import torch
import torchaudio
from TTS.api import TTS

# Load XTTS v2 model
print("Loading XTTS v2 model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
print("Model loaded!")


def convert_to_wav(input_path):
    """Convert audio to WAV format for XTTS"""
    output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    
    try:
        waveform, sample_rate = torchaudio.load(input_path)
        
        # Convert to mono
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Resample to 22050 Hz
        if sample_rate != 22050:
            resampler = torchaudio.transforms.Resample(sample_rate, 22050)
            waveform = resampler(waveform)
        
        torchaudio.save(output_path, waveform, 22050)
        return output_path
    except Exception as e:
        print(f"Conversion error: {e}")
        return input_path


def generate_speech(text, voice_audio, language, speed):
    """Generate speech from text using voice sample"""
    
    if not text or not text.strip():
        return None, "Please enter text to convert"
    
    if voice_audio is None:
        return None, "Please provide a voice sample"
    
    try:
        # Convert voice to WAV
        wav_path = convert_to_wav(voice_audio)
        
        # Generate output
        output_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
        
        tts_model.tts_to_file(
            text=text.strip(),
            speaker_wav=wav_path,
            language=language,
            file_path=output_path,
            speed=speed
        )
        
        # Clean up
        if wav_path != voice_audio:
            os.unlink(wav_path)
        
        return output_path, "Success!"
        
    except Exception as e:
        return None, f"Error: {str(e)}"


def generate_speech_base64(text, voice_base64, language, speed):
    """API endpoint for base64 voice input"""
    
    if not text or not voice_base64:
        return {"error": "Missing text or voice data"}
    
    try:
        # Decode base64 voice
        if ',' in voice_base64:
            header, data = voice_base64.split(',', 1)
        else:
            data = voice_base64
        
        audio_bytes = base64.b64decode(data)
        
        # Determine format
        suffix = '.wav'
        if 'audio/mp3' in voice_base64 or 'audio/mpeg' in voice_base64:
            suffix = '.mp3'
        elif 'audio/m4a' in voice_base64:
            suffix = '.m4a'
        elif 'audio/webm' in voice_base64:
            suffix = '.webm'
        
        # Save temp file
        voice_path = tempfile.NamedTemporaryFile(suffix=suffix, delete=False).name
        with open(voice_path, 'wb') as f:
            f.write(audio_bytes)
        
        # Generate
        output_path, message = generate_speech(text, voice_path, language, speed)
        
        # Clean up
        os.unlink(voice_path)
        
        if output_path:
            # Read and encode output
            with open(output_path, 'rb') as f:
                audio_data = base64.b64encode(f.read()).decode('utf-8')
            os.unlink(output_path)
            
            return {
                "success": True,
                "audio": f"data:audio/wav;base64,{audio_data}"
            }
        else:
            return {"error": message}
            
    except Exception as e:
        return {"error": str(e)}


# Gradio Interface
with gr.Blocks(title="My Voice - Voice Cloning TTS") as demo:
    gr.Markdown("# My Voice - Voice Cloning TTS")
    gr.Markdown("Clone any voice and generate speech from text using XTTS v2")
    
    with gr.Row():
        with gr.Column():
            text_input = gr.Textbox(
                label="Text to speak",
                placeholder="Enter the text you want to convert to speech...",
                lines=5
            )
            
            voice_input = gr.Audio(
                label="Voice sample (10-30 seconds recommended)",
                type="filepath"
            )
            
            with gr.Row():
                language = gr.Dropdown(
                    label="Language",
                    choices=[
                        ("English", "en"),
                        ("Spanish", "es"),
                        ("French", "fr"),
                        ("German", "de"),
                        ("Italian", "it"),
                        ("Portuguese", "pt"),
                        ("Polish", "pl"),
                        ("Turkish", "tr"),
                        ("Russian", "ru"),
                        ("Dutch", "nl"),
                        ("Czech", "cs"),
                        ("Arabic", "ar"),
                        ("Chinese", "zh"),
                        ("Japanese", "ja"),
                        ("Korean", "ko"),
                        ("Hindi", "hi"),
                    ],
                    value="en"
                )
                
                speed = gr.Slider(
                    label="Speed",
                    minimum=0.5,
                    maximum=2.0,
                    value=1.0,
                    step=0.1
                )
            
            generate_btn = gr.Button("Generate Speech", variant="primary")
        
        with gr.Column():
            output_audio = gr.Audio(label="Generated Audio", type="filepath")
            status = gr.Textbox(label="Status", interactive=False)
    
    generate_btn.click(
        fn=generate_speech,
        inputs=[text_input, voice_input, language, speed],
        outputs=[output_audio, status]
    )
    
    # API endpoint
    gr.Markdown("---")
    gr.Markdown("### API Usage")
    gr.Markdown("""
    ```
    POST /api/predict
    {
        "data": [
            "Text to speak",
            "data:audio/wav;base64,...",  // Base64 voice
            "en",                          // Language
            1.0                            // Speed
        ]
    }
    ```
    """)

# Enable API
demo.queue()

if __name__ == "__main__":
    demo.launch()
