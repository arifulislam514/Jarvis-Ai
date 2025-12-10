import pygame
import random
import asyncio
import edge_tts
import os
from dotenv import dotenv_values

# Base dir = project root (JARVIS AI)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # go up one level
ENV_PATH = os.path.join(BASE_DIR, ".env")

env_vars = dotenv_values(ENV_PATH)
AssistantVoice = env_vars.get("AssistantVoice")

if not AssistantVoice:
    raise ValueError("AssistantVoice is missing from .env file.")

# 🔹 Use an absolute path for the audio file
AUDIO_PATH = os.path.join(BASE_DIR, "Data", "speech.mp3")
print("AUDIO_PATH:", AUDIO_PATH)  # debug

# Asynchronous function to convert text to an audio file 
async def TextToAudioFile(text: str) -> None:
    # Ensure folder exists
    os.makedirs(os.path.dirname(AUDIO_PATH), exist_ok=True)

    # Remove old file if present
    if os.path.exists(AUDIO_PATH):
        os.remove(AUDIO_PATH)

    print("Saving TTS to:", AUDIO_PATH)  # debug

    communicate = edge_tts.Communicate(text, AssistantVoice, pitch="+5Hz", rate="+13%")
    await communicate.save(AUDIO_PATH)

# Function to manage Text-to-Speech (TTS) functionality 
def TTS(text: str, func=lambda r=None: True):
    while True:
        try:
            # Convert text to an audio file asynchronously 
            asyncio.run(TextToAudioFile(text))
            
            # Initialize pygame mixer for audio playback 
            pygame.mixer.init()
            
            # Load the generated speech file into pygame mixer 
            pygame.mixer.music.load(AUDIO_PATH)
            pygame.mixer.music.play()
            
            # Loop until the audio is done playing or the function stops
            while pygame.mixer.music.get_busy():
                if func() is False:
                    break
                pygame.time.Clock().tick(10)  # Limit the loop to 10 ticks per second
                
            return True  # Return True if the audio played successfully
        
        except Exception as e:
            # Print the real error this time
            print(f"Error in TTS: {e}")
            return False
            
        finally:
            try:
                # Call the provided function with False to signal the end of TTS
                func(False)

                # Only stop/quit if mixer was initialized
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                
            except Exception as e:
                print(f"Error in TTS Cleanup: {e}")


# Function to manage Text-to-Speech with additional responses for long text
def TextToSpeech(Text, func=lambda r=None: True):
    Data = str(Text).split('.')  # Split the text into sentences based on periods
    
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
    
    # If the text is very long (more than 4 sentences and 250 characters), add a response message
    if len(Data) > 4 and len(Text) >= 250:
        # Speak first 2 sentences + one random “check the screen” message
        spoken_part = " ".join(Text.split('.')[0:2]).strip()
        extra_msg = random.choice(responses)
        full_spoken = (spoken_part + ". " + extra_msg).strip()
        TTS(full_spoken, func)
    else:
        # Otherwise, speak the entire text
        TTS(Text, func)


# Main execution loop
if __name__ == "__main__":
    while True:
        TextToSpeech(input("Enter Text: "))
        # Or, if you want raw TTS without long-text behavior:
        # TTS(input("Enter Text: "))
