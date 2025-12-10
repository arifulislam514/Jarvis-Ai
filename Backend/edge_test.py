import asyncio
import edge_tts
import os

VOICE = "en-US-AriaNeural"
AUDIO_PATH = "test_edge.mp3"

async def main():
    print("Using voice:", VOICE)
    tts = edge_tts.Communicate("hello from edge tts", VOICE)
    await tts.save(AUDIO_PATH)

asyncio.run(main())
print("Saved file at:", os.path.abspath(AUDIO_PATH))
print("File size (bytes):", os.path.getsize(AUDIO_PATH))
