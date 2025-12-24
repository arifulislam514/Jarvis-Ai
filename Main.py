"""
Jarvis AI - Main entry point

This project originally shipped with a PyQt GUI. The UI has been replaced with an
Eel (HTML/JS) frontend located at: Frontend/web/frontend/

Run:
    python Main.py

Notes:
- Make sure you have a valid .env in the project root.
- Install requirements (Requirements.txt) including `eel`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import traceback
from asyncio import run as asyncio_run
from time import sleep
from typing import List, Optional, Tuple

try:
    import eel  # type: ignore
except ModuleNotFoundError as e:
    raise SystemExit(
        "Missing dependency 'eel'. Install dependencies with: pip install -r Requirements.txt"
    ) from e

from dotenv import dotenv_values

# ----------------------------
# Paths / environment
# ----------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

ENV_VARS = dotenv_values(os.path.join(BASE_DIR, ".env"))

USERNAME = ENV_VARS.get("Username") or ENV_VARS.get("username") or "User"
ASSISTANT_NAME = ENV_VARS.get("Assistantname") or ENV_VARS.get("AssistantName") or "Jarvis"

DATA_DIR = os.path.join(BASE_DIR, "Data")
CHATLOG_PATH = os.path.join(DATA_DIR, "ChatLog.json")

FRONTEND_DIR = os.path.join(BASE_DIR, "Frontend")
FRONTEND_FILES_DIR = os.path.join(FRONTEND_DIR, "Files")
WEB_DIR = os.path.join(FRONTEND_DIR, "web")  # contains: WEB_DIR/frontend/index.html
WEB_START_PAGE = "frontend/index.html"

IMAGE_GEN_FILE = os.path.join(FRONTEND_FILES_DIR, "ImageGeneration.data")

DEFAULT_MESSAGE = (
    f"{USERNAME} : Hello {ASSISTANT_NAME}, How are you?\n"
    f"{ASSISTANT_NAME} : Welcome {USERNAME}. I am doing well. How may I help you?"
)

# Commands that should be sent to Automation()
AUTOMATION_PREFIXES = [
    "open",
    "close",
    "play",
    "system",
    "content",
    "google search",
    "youtube search",
]

# Keep track of spawned subprocesses (e.g., image generation)
_SUBPROCESSES: List[subprocess.Popen] = []


# ----------------------------
# Small helpers
# ----------------------------

def _eel_safe(fn_name: str, *args):
    """Call a JS function exposed via Eel, ignoring errors if UI isn't ready."""
    try:
        fn = getattr(eel, fn_name)
        fn(*args)
    except Exception:
        # UI might not be connected yet; ignore
        pass


def AnswerModifier(answer: str) -> str:
    lines = (answer or "").split("\n")
    non_empty = [ln for ln in lines if ln.strip()]
    return "\n".join(non_empty)


def QueryModifier(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return ""

    # Detect if it's a question (best-effort)
    is_question = q.endswith("?") or q.lower().startswith(
        (
            "how",
            "what",
            "who",
            "where",
            "when",
            "why",
            "which",
            "whose",
            "whom",
            "can you",
            "could you",
            "would you",
            "is",
            "are",
            "do",
            "does",
            "did",
            "will",
            "shall",
            "may",
            "might",
        )
    )

    # strip trailing punctuation
    q = re.sub(r"[\s\.\?!]+$", "", q).strip()
    if not q:
        return ""

    q = q[0].upper() + q[1:] if len(q) > 1 else q.upper()
    return q + ("?" if is_question else ".")


def _norm_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[\s\.,;:!\?]+$", "", t)
    return t


def _ensure_dirs_and_files() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FRONTEND_FILES_DIR, exist_ok=True)

    # chat log
    if not os.path.exists(CHATLOG_PATH):
        with open(CHATLOG_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

    # core frontend files used by backend scripts
    for fname, default in [
        ("Database.data", ""),
        ("Responses.data", ""),
        ("Status.data", "Available..."),
        ("Mic.data", "False"),
        ("LastRaw.data", ""),
        ("LastLang.data", ""),
        ("LastEnglish.data", ""),
        ("ImageGeneration.data", ""),
    ]:
        fpath = os.path.join(FRONTEND_FILES_DIR, fname)
        if not os.path.exists(fpath):
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(default)


def _load_chatlog() -> list:
    try:
        with open(CHATLOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_chatlog(data: list) -> None:
    try:
        with open(CHATLOG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _seed_default_chat_if_empty() -> None:
    data = _load_chatlog()
    if data:
        return
    seeded = [
        {"role": "user", "content": f"Hello {ASSISTANT_NAME}, How are you?"},
        {"role": "assistant", "content": f"Welcome {USERNAME}. I am doing well. How may I help you?"},
    ]
    _save_chatlog(seeded)


def _ui_status(status: str) -> None:
    # short status line (top / siri message area)
    _eel_safe("DisplayMessage", status)


def _ui_user(message: str) -> None:
    _eel_safe("senderText", message)


def _ui_assistant(message: str) -> None:
    _eel_safe("receiverText", message)


def _ui_idle() -> None:
    _eel_safe("ShowHood")
    _ui_status("Available...")


def _speech_recognition() -> str:
    try:
        from Backend.SpeechToText import SpeechRecognition
        return SpeechRecognition() or ""
    except Exception as e:
        _ui_assistant(f"Speech recognition error: {e}")
        return ""


def _speak(text: str) -> None:
    try:
        from Backend.TextToSpeech import TextToSpeech
        TextToSpeech(text)
    except Exception:
        # TTS failure shouldn't crash the assistant
        pass


# ----------------------------
# Email flow (voice-guided)
# ----------------------------

def _assistant_say(text: str, speak: bool = True) -> None:
    msg = AnswerModifier(text)
    _ui_assistant(msg)
    _ui_status("Answering ...")
    if speak:
        _speak(msg)


def _ask_user(prompt: str) -> str:
    _assistant_say(prompt, speak=True)
    _ui_status("Listening ...")
    ans = _speech_recognition()
    if ans:
        _ui_user(ans)
    return ans


def SendEmailFlow(initial_command: str = "") -> bool:
    """Interactive send-email flow.

    Triggered when the user says "send email" or when the DMM outputs a send-email task.
    """
    from Backend.Automation import SendEmailSMTP
    from Backend.EmailAssistant import (
        extract_emails,
        clean_subject,
        maybe_extract_subject,
        maybe_extract_about,
        draft_email_body,
    )

    cmd = initial_command or ""

    # 1) Recipient(s)
    recipients = extract_emails(cmd)
    if not recipients:
        r_text = _ask_user("Please tell me the recipient email address.")
        recipients = extract_emails(r_text)

    if not recipients:
        r_text = _ask_user("I couldn't detect a valid email address. Please say it again, like john@example.com.")
        recipients = extract_emails(r_text)

    if not recipients:
        _assistant_say("Sorry, I still couldn't detect a valid email address, so I cancelled sending the email.")
        return False

    # 2) Subject
    subject = maybe_extract_subject(cmd)
    if not subject:
        subject = _ask_user("What should the email subject be?")
    subject = clean_subject(subject)

    if not subject:
        _assistant_say("I didn't catch a subject. Cancelling the email.")
        return False

    about = maybe_extract_about(cmd)

    # 3) Draft email body (or use provided body)
    body_match = re.search(r"\bbody\b\s+(.*)$", cmd, flags=re.I)
    provided_body = (body_match.group(1).strip() if body_match else "")

    _ui_status("Writing email...")
    body = provided_body or draft_email_body(subject=subject, about=about)

    # preview
    _ui_assistant(
        "Draft email\n"
        f"To: {', '.join(recipients)}\n"
        f"Subject: {subject}\n\n"
        f"{body}"
    )
    _speak("Okay. I drafted the email and I am sending it now.")

    # 4) Send
    _ui_status("Sending email...")
    ok: List[str] = []
    failed: List[Tuple[str, str]] = []
    for to_addr in recipients:
        res = SendEmailSMTP(to_addr, subject, body)
        if res is True:
            ok.append(to_addr)
        else:
            failed.append((to_addr, str(res)))

    # 5) Report result
    if ok and not failed:
        _assistant_say("Email sent successfully.")
        return True

    lines: List[str] = []
    if ok:
        lines.append(f"✅ Sent to: {', '.join(ok)}")
    if failed:
        lines.append("❌ Failed:")
        for to_addr, err in failed:
            lines.append(f"  - {to_addr}: {err}")

    _ui_assistant("\n".join(lines))
    _assistant_say("I couldn't send the email to everyone. Please check the chat for details.")
    return False


# ----------------------------
# Core assistant logic
# ----------------------------

def _run_image_generation(prompt: str) -> None:
    os.makedirs(FRONTEND_FILES_DIR, exist_ok=True)

    with open(IMAGE_GEN_FILE, "w", encoding="utf-8") as f:
        f.write(f"{prompt},True")

    script_path = os.path.join(BASE_DIR, "Backend", "ImageGeneration.py")
    if not os.path.exists(script_path):
        _ui_assistant(f"Image generator not found: {script_path}")
        return

    try:
        p = subprocess.Popen(
            [sys.executable, script_path],
            cwd=BASE_DIR,          # important on Windows
            shell=False,
        )
        _SUBPROCESSES.append(p)
        print("IMAGE: started process PID =", p.pid)
    except Exception as e:
        _ui_assistant(f"Error starting image generation: {e}")
        print("IMAGE ERROR:", repr(e))


def _process_query(query: str) -> None:
    """Process a single user query.

    Priority:
    1) Direct commands (send email / generate image / pure automation)
    2) DMM routing (Cohere) when available
    3) Heuristic routing if DMM isn't configured
    4) General chat fallback
    """

    query = (query or "").strip()
    if not query:
        return

    q_norm = _norm_cmd(query)

    # ------------------------
    # Direct intents (no DMM)
    # ------------------------

    # Exit shortcuts
    if q_norm in {"exit", "quit", "bye", "goodbye"}:
        _assistant_say("Okay, bye!", speak=True)
        os._exit(0)

    # Email commands: handle even if the decision model isn't available.
    if q_norm.startswith("send email") or q_norm.startswith("email "):
        SendEmailFlow(initial_command=query)
        return

    # Image requests like: "supercar image", "car photo", "generate a picture of a tiger"
    if re.search(r"\b(image|photo|picture|wallpaper)\b", q_norm) and not q_norm.startswith("generate image"):
        # remove common filler words to form a clean prompt
        prompt = re.sub(r"\b(show me|give me|generate|create|make|an|a|the|of|please)\b", "", q_norm)
        prompt = re.sub(r"\b(image|photo|picture|wallpaper)\b", "", prompt).strip()

        if prompt:
            _ui_status("Generating image...")
            _assistant_say("Generating the image.", speak=True)
            _run_image_generation(prompt)
        else:
            _assistant_say("Please tell me what image you want me to generate.", speak=True)
        return

    # Image generation commands
    if q_norm.startswith("generate image"):
        prompt = q_norm.removeprefix("generate image").strip().strip(".")
        if prompt:
            _ui_status("Generating image...")
            _assistant_say("Generating the image.", speak=True)
            _run_image_generation(prompt)
        else:
            _assistant_say("Please tell me what image you want me to generate.", speak=True)
        return

    # If it's a *pure* automation command (open/close/play/etc.) run it directly.
    if any(q_norm.startswith(p) for p in AUTOMATION_PREFIXES) and (" and " not in q_norm) and ("," not in q_norm):
        try:
            from Backend.Automation import Automation
            asyncio_run(Automation([q_norm]))
            _assistant_say("Done.", speak=True)
        except Exception as e:
            _ui_assistant(f"Automation error: {e}")
        return

    _ui_status("Thinking ...")

    # ------------------------
    # Decision model routing
    # ------------------------

    decision: List[str] = []
    dmm_error: Optional[Exception] = None

    try:
        from Backend.Model import FirstLayerDMM
        decision = FirstLayerDMM(query)
        if not isinstance(decision, list):
            decision = []
    except Exception as e:
        dmm_error = e
        decision = []

    print("\n=== DEBUG: DMM ===")
    print("q_norm:", repr(q_norm))
    print("dmm_error:", repr(dmm_error))
    print("decision:", decision)
    print("=== /DEBUG ===\n")

    # ------------------------
    # If DMM is missing, do a lightweight heuristic routing
    # ------------------------

    if dmm_error is not None:
        # Split compound commands ("open chrome and tell me about X")
        parts = [p.strip() for p in re.split(r"\b(?:and then|then|and)\b|[;,]+", q_norm) if p.strip()]

        automation_tasks: List[str] = []
        general_parts: List[str] = []

        for p in parts:
            if p in {"exit", "quit", "bye", "goodbye"}:
                _assistant_say("Okay, bye!", speak=True)
                os._exit(0)

            if p.startswith("send email") or p.startswith("email "):
                SendEmailFlow(initial_command=p)
                continue

            if p.startswith("generate image"):
                prompt = p.removeprefix("generate image").strip().strip(".")
                if prompt:
                    _ui_status("Generating image...")
                    _assistant_say("Generating the image.", speak=True)
                    _run_image_generation(prompt)
                continue

            if any(p.startswith(ap) for ap in AUTOMATION_PREFIXES):
                automation_tasks.append(p)
                continue

            general_parts.append(p)

        if automation_tasks:
            try:
                from Backend.Automation import Automation
                asyncio_run(Automation(automation_tasks))
            except Exception as e:
                _ui_assistant(f"Automation error: {e}")

        if general_parts:
            # Use chatbot on the remaining part
            try:
                from Backend.Chatbot import ChatBot
                q_final = QueryModifier(" ".join(general_parts))
                ans = ChatBot(q_final)
                ans = AnswerModifier(ans)
                _assistant_say(ans, speak=True)
            except Exception as e:
                _ui_assistant(f"Chatbot error: {e}")
        else:
            # If we only executed tasks, we're done.
            if automation_tasks:
                _assistant_say("Done.", speak=True)

        # (Optional) show why the decision model is unavailable
        _ui_assistant(f"(Decision model unavailable; using fallback routing. {dmm_error})")
        return

    # ------------------------
    # DMM-based execution
    # ------------------------

    # Handle send-email tasks in decision
    email_tasks = [t for t in decision if t.strip().startswith("send email")]
    if email_tasks:
        for t in email_tasks:
            SendEmailFlow(initial_command=t)

    # Trigger image generation tasks
    did_generate_image = False
    for t in decision:
        if t.startswith("generate image"):
            prompt = t.removeprefix("generate image").strip().strip(".")
            if prompt:
                _ui_status("Generating image...")
                _assistant_say("Generating the image.", speak=True)
                _run_image_generation(prompt)
                did_generate_image = True

    # Run automation tasks
    automation_tasks = [t for t in decision if any(t.startswith(p) for p in AUTOMATION_PREFIXES)]
    if automation_tasks:
        try:
            from Backend.Automation import Automation
            asyncio_run(Automation(automation_tasks))
        except Exception as e:
            _ui_assistant(f"Automation error: {e}")

    # IMPORTANT: If this was an image-only request, do NOT also produce a chatbot answer.
    # (This prevents responses like "I'm a text-based AI, I can't display images..." after
    # the image has already been generated.)
    if did_generate_image:
        wants_text_too = bool(
            re.search(
                r"\b(tell\s+me|describe|explain|about|details|information|specs?|history|compare)\b",
                q_norm,
            )
        )
        if not wants_text_too:
            # If we only did tasks (image/automation/email), we're done.
            if automation_tasks or email_tasks:
                _assistant_say("Done.", speak=True)
            return

    # Answering logic (general / realtime)
    G = any(t.startswith("general") for t in decision)
    R = any(t.startswith("realtime") for t in decision)

    merged = " and ".join(
        [" ".join(t.split()[1:]).strip() for t in decision if t.startswith("general") or t.startswith("realtime")]
    ).strip()

    # Exit
    if any(t == "exit" or t.strip() == "exit" for t in decision):
        _assistant_say("Okay, bye!", speak=True)
        os._exit(0)

    # If both general+realtime, prefer realtime search on the merged query
    if G and R:
        try:
            from Backend.RealtimeSearchEngine import RealtimeSearchEngine
            _ui_status("Searching...")
            ans = RealtimeSearchEngine(QueryModifier(merged or query))
            ans = AnswerModifier(ans)
            _assistant_say(ans, speak=True)
            return
        except Exception as e:
            _ui_assistant(f"Realtime search error: {e}")

    # Otherwise, execute first relevant answer task
    for t in decision:
        if t.startswith("general"):
            try:
                from Backend.Chatbot import ChatBot
                q_final = t.removeprefix("general").strip() or query
                _ui_status("Thinking ...")
                ans = ChatBot(q_final)
                ans = AnswerModifier(ans)
                _assistant_say(ans, speak=True)
                return
            except Exception as e:
                _ui_assistant(f"Chatbot error: {e}")
                return

        if t.startswith("realtime"):
            try:
                from Backend.RealtimeSearchEngine import RealtimeSearchEngine
                _ui_status("Searching ...")
                ans = RealtimeSearchEngine(query)
                ans = AnswerModifier(ans)
                _assistant_say(ans, speak=True)
                return
            except Exception as e:
                _ui_assistant(f"Realtime search error: {e}")
                return

    # If we got here, there wasn't a conversational answer task.
    if automation_tasks or email_tasks:
        _assistant_say("Done.", speak=True)
    else:
        # Last-resort fallback
        try:
            from Backend.Chatbot import ChatBot
            ans = ChatBot(query)
            _assistant_say(ans, speak=True)
        except Exception:
            _assistant_say("Sorry, I couldn't process that request.")



# ----------------------------
# Eel exposed functions (called from JS)
# ----------------------------

@eel.expose
def init() -> bool:
    """Called once from the web UI when it is ready."""
    _ensure_dirs_and_files()
    _seed_default_chat_if_empty()

    # Smooth startup animations (safe even if any are missing)
    _eel_safe("hideLoader")
    sleep(1.0)
    _eel_safe("hideFaceAuth")
    sleep(1.0)
    _eel_safe("hideFaceAuthSuccess")
    sleep(0.8)
    _eel_safe("hideStart")
    sleep(0.5)

    # Load previous chat
    history = _load_chatlog()[-50:]
    for item in history:
        role = (item.get("role") or "").lower()
        content = str(item.get("content") or "")
        if not content.strip():
            continue
        if role == "user":
            _ui_user(content)
        else:
            _ui_assistant(content)

    _ui_idle()
    return True


@eel.expose
def play_assistant_sound() -> bool:
    """Optional click sound when the mic button is pressed."""
    try:
        sound_path = os.path.join(WEB_DIR, "frontend", "assets", "audio", "start_sound.mp3")
        if not os.path.exists(sound_path):
            return False

        import pygame  # noqa: WPS433

        # Avoid breaking TTS if mixer is already in use.
        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(sound_path)
        pygame.mixer.music.play()
        return True
    except Exception:
        return False


@eel.expose
def takeAllCommands(message: Optional[str] = None) -> bool:
    """Main entry point called from the UI.

    - If `message` is empty/None -> use voice input
    - Otherwise -> treat `message` as a typed command
    """
    try:
        msg = (message or "").strip()

        if not msg:
            _ui_status("Listening ...")
            query = _speech_recognition().strip()
        else:
            query = msg

        if not query:
            _ui_idle()
            return True

        print("\n=== DEBUG: takeAllCommands ===")
        print("QUERY_FROM_UI:", repr(query))
        print("=== /DEBUG ===\n")

        _ui_user(query)
        _process_query(query)

    except Exception:
        _ui_assistant("Sorry, something went wrong. Check the console for details.")
        traceback.print_exc()
    finally:
        _ui_idle()

    return True


# ----------------------------
# App start
# ----------------------------

def _start_eel() -> None:
    if not os.path.isdir(WEB_DIR):
        raise RuntimeError(f"Web directory not found: {WEB_DIR}")

    eel.init(WEB_DIR)

    # Try Chrome first, fall back to default browser if not available.
    try:
        eel.start(WEB_START_PAGE, size=(1200, 750), mode="chrome", block=True)
    except Exception:
        eel.start(WEB_START_PAGE, size=(1200, 750), block=True)


if __name__ == "__main__":
    _ensure_dirs_and_files()
    _start_eel()
