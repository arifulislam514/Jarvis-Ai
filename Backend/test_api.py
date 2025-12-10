import pygame
import random
import asyncio
import edge_tts
import os
from dotenv import dotenv_values

env_vars = dotenv_values(".env")
AssistantVoice = env_vars.get("AssistantVoice") or "en-US-JennyNeural"

async def TextToAudioFile(text: str, out_path: str = r"Data\speech.mp3") -> None:
    # Ensure output directory exists
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Remove old file if present (optional)
    if os.path.exists(out_path):
        try:
            os.remove(out_path)
        except Exception:
            pass

    # Create and save speech file (always generate)
    communicate = edge_tts.Communicate(text, AssistantVoice, pitch='+5Hz', rate='+13%')
    await communicate.save(out_path)

def TTS(Text: str, func=lambda r=None: True, max_retries: int = 1) -> bool:
    retries = 0
    out_path = r"Data\speech.mp3"

    while retries < max_retries:
        try:
            # Generate audio file (blocking call from sync code)
            asyncio.run(TextToAudioFile(Text, out_path))

            # Initialize pygame mixer if not already initialized
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            # Load and play
            pygame.mixer.music.load(out_path)
            pygame.mixer.music.play()

            # Wait while playing, allow external func to stop playback
            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                if func() is False:
                    pygame.mixer.music.stop()
                    break
                clock.tick(10)

            # Signal end and return success
            try:
                func(False)
            except Exception:
                pass

            return True

        except Exception as e:
            print(f"Error in TTS: {e}")
            retries += 1

        finally:
            try:
                func(False)
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
            except Exception as e:
                print(f"Error in TTS Cleanup: {e}")

    return False

def TextToSpeech(Text: str, func=lambda r=None: True):
    Data = str(Text).split('.')
    responses = [
        "The rest of the result has been printed to the chat screen, kindly check it out sir.",
        "The rest of the text is now on the chat screen, sir, please check it.",
        "You can see the rest of the text on the chat screen, sir.",
        "The remaining part of the text is now on the chat screen, sir.",
        "Sir, you'll find more text on the chat screen for you to see.",
        "The rest of the answer is now on the chat screen, sir.",
        "Sir, please look at the chat screen, the rest of the answer is there.",
        "You'll find the complete answer on the chat screen, sir.",
        "The next part of the text is on the chat screen, sir.",
        "Sir, please check the chat screen for more information.",
        "There's more text on the chat screen for you, sir.",
        "Sir, take a look at the chat screen for additional text.",
        "You'll find more to read on the chat screen, sir.",
        "Sir, check the chat screen for the rest of the text.",
        "The chat screen has the rest of the text, sir.",
        "There's more to see on the chat screen, sir, please look.",
        "Sir, the chat screen holds the continuation of the text.",
        "You'll find the complete answer on the chat screen, kindly check it out sir.",
        "Please review the chat screen for the rest of the text, sir.",
        "Sir, look at the chat screen for the complete answer."
    ]

    if len(Data) > 4 and len(Text) >= 250:
        # Speak the first two sentences and then a short response
        first_part = " ".join(Text.split('.')[:2]).strip()
        if first_part and not first_part.endswith('.'):
            first_part += '.'
        extra = random.choice(responses)
        TTS(f"{first_part} {extra}", func)
    else:
        TTS(Text, func)

        
# Main exeution loop
if __name__ == "__main__":
    
    while True:
        # Prompt user for input and pass it to TextToSpeech function
        # if want to ignore long text, use this.
        TextToSpeech(input("Enter Text: "))
        
        # if want to use long text, uncomment next line.
        # TTS(input("Enter Text: "))
        