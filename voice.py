import asyncio
import edge_tts
import tempfile
import os
import ctypes
import time
from typing import Optional


def play_mp3_windows(file_path: str):
    """Play an MP3 file using Windows built-in winmm.dll (no extra packages needed)."""
    winmm = ctypes.windll.winmm
    
    # Open the MP3 file
    winmm.mciSendStringW(f'open "{file_path}" type mpegvideo alias hunti_audio', None, 0, 0)
    # Play it
    winmm.mciSendStringW('play hunti_audio', None, 0, 0)
    
    # Wait for it to finish playing
    status = ctypes.create_unicode_buffer(256)
    while True:
        winmm.mciSendStringW('status hunti_audio mode', status, 256, 0)
        if status.value != 'playing':
            break
        time.sleep(0.1)
        
    # Close the file
    winmm.mciSendStringW('close hunti_audio', None, 0, 0)


def speak_text(text: str, rate: int = 150, volume: float = 1.0) -> None:
    """Speak text using edge-tts."""
    if not text:
        return
    
    try:
        asyncio.run(_speak_async(text, rate))
    except Exception as exc:
        print(f"TTS error: {exc}")


async def _speak_async(text: str, rate: int) -> None:
    """Generate and play speech."""
    voice = "en-US-GuyNeural"  # Natural male voice
    
    # Create temp file
    temp_dir = tempfile.gettempdir()
    output_file = os.path.join(temp_dir, "hunti_tts.mp3")
    
    # Generate speech
    rate_adjustment = f"+{rate - 100}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_adjustment)
    await communicate.save(output_file)
    
    # Play using the native Windows method
    try:
        play_mp3_windows(output_file)
    except Exception as play_error:
        print(f"Playback error: {play_error}")
    finally:
        # Cleanup
        try:
            os.remove(output_file)
        except:
            pass


def speak_thought(thought: Optional[str], rate: int = 150, volume: float = 1.0) -> None:
    """Speak the thought returned by the AI."""
    if thought:
        speak_text(str(thought), rate=rate, volume=volume)


if __name__ == "__main__":
    print("Testing voice...")
    speak_thought("Hello! This is Hunti AI speaking. Can you hear me now?")
    print("Done.")