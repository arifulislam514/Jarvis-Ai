from Backend.Model import FirstLayerDMM
from Backend.Automation import Automation
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech

from dotenv import dotenv_values
from asyncio import run
import subprocess
import os

# --------- ENV + GLOBALS --------- #

env_vars = dotenv_values(".env")

Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Assistant")

subprocesses = []

# Keywords that trigger Automation (Backend/Automation.py)
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]


def MainExecution():
    """
    Main voice interaction:
    - Listens to user
    - Uses FirstLayerDMM for intent classification
    - Supports Automation, Image generation, ChatBot
    - Speaks responses using TextToSpeech
    """

    TaskExecution = False
    ImageExecution = False
    ImageGenerationQuery = ""

    # 1. Listen
    print(f"\n[{Assistantname}] Listening...")
    Query = SpeechRecognition()
    print(f"{Username}: {Query}")

    # 2. Intent Analysis
    print(f"[{Assistantname}] Thinking...")
    Decision = FirstLayerDMM(Query)
    print(f"[DEBUG] Decision: {Decision}")

    # 3. Image Generation Detection
    for q in Decision:
        if "generate" in q:
            ImageGenerationQuery = q
            ImageExecution = True

    # 4. Automation Commands
    for q in Decision:
        if not TaskExecution and any(q.startswith(func) for func in Functions):
            try:
                run(Automation(list(Decision)))
            except Exception as e:
                print(f"[ERROR] Automation error: {e}")
            TaskExecution = True

    # 5. Execute Image Generation if needed
    if ImageExecution:
        try:
            with open("Frontend/Files/ImageGeneratoion.data", "w", encoding="utf-8") as f:
                f.write(f"{ImageGenerationQuery}, True")

            p = subprocess.Popen(
                ["python", "Backend/ImageGeneration.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                shell=False,
            )
            subprocesses.append(p)

        except Exception as e:
            print(f"[ERROR] Image Generation failed: {e}")

    # 6. Handle ChatBot / exit command
    for q in Decision:

        # Normal chatbot response ("general ...")
        if "general" or "realtime" in q:
            QueryFinal = q.replace("general", "", 1).strip()
            Answer = ChatBot(QueryFinal)
            print(f"{Assistantname}: {Answer}")
            TextToSpeech(Answer)
            return True

        # Exit command
        if "exit" in q:
            Answer = ChatBot("Goodbye!")
            print(f"{Assistantname}: {Answer}")
            TextToSpeech(Answer)
            os._exit(0)

    return False


def main():
    print(f"=== {Assistantname} is ready ===")
    print("Speak any time. Press Ctrl+C to exit.\n")

    while True:
        try:
            MainExecution()
        except KeyboardInterrupt:
            print("\nExiting program...")
            break
        except Exception as e:
            print(f"[ERROR] Unexpected: {e}")


if __name__ == "__main__":
    main()
