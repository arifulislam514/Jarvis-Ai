from Frontend. GUI import ( 
GraphicalUserInterface, 
SetAssistantStatus, 
ShowTextToScreen,
TempDirectoryPath,
SetMicrophoneStatus,
AnswerModifier, 
QueryModifier, 
GetMicrophoneStatus,
GetAssistantStatus)
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.Automation import Automation, SendEmailSMTP
from Backend.EmailAssistant import (
    extract_emails,
    clean_subject,
    maybe_extract_subject,
    maybe_extract_about,
    draft_email_body,
)
from Backend.SpeechToText import SpeechRecognition
from Backend.Chatbot import ChatBot
from Backend.TextToSpeech import TextToSpeech
from dotenv import dotenv_values
from asyncio import run
from time import sleep 
import subprocess
import threading 
import json 
import os
import sys
import re

env_vars= dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessage = f''' {Username} : Hello {Assistantname}, How are you?
{Assistantname} Welcome {Username}. I am doing well. How may i help you?''' 
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]


def _norm_cmd(text: str) -> str:
    """Normalize short voice commands (strip trailing punctuation)."""
    t = (text or "").strip().lower()
    t = re.sub(r"[\s\.,;:!\?]+$", "", t)
    return t


def _speak_and_show(text: str):
    ShowTextToScreen(f" {Assistantname} : {text}")
    SetAssistantStatus("Answering...")
    TextToSpeech(text)


def _ask_user(prompt: str) -> str:
    """Ask the user a question via TTS, then listen for their reply."""
    _speak_and_show(prompt)
    SetAssistantStatus("Listening ... ")
    ans = SpeechRecognition()
    ShowTextToScreen(f"{Username} : {ans}")
    return ans


def SendEmailFlow(initial_command: str = "") -> bool:
    """Interactive email flow.

    Triggered when the user says "send email".
    - Ask recipient email
    - Ask subject
    - Draft a well-structured email body
    - Send via SMTP
    """

    # 1) Recipient(s)
    recipients = extract_emails(initial_command)
    if not recipients:
        r_text = _ask_user("Please tell me the recipient email address.")
        recipients = extract_emails(r_text)

    # one retry if STT didn't capture an email cleanly
    if not recipients:
        r_text = _ask_user("I couldn't detect a valid email address. Please say it again, like john@example.com.")
        recipients = extract_emails(r_text)

    if not recipients:
        _speak_and_show("Sorry, I still couldn't detect a valid email address, so I cancelled sending the email.")
        return False

    # 2) Subject
    subject = maybe_extract_subject(initial_command)
    if not subject:
        subject = _ask_user("What should the email subject be?")
    subject = clean_subject(subject)

    if not subject:
        _speak_and_show("I didn't catch a subject. Cancelling the email.")
        return False

    # Optional context if user said: "send email ... about ..."
    about = maybe_extract_about(initial_command)

    # 3) Draft email body (or use provided body)
    # Supports commands like: "send email to a@b.com subject X body Y"
    body_match = re.search(r"\bbody\b\s+(.*)$", initial_command or "", flags=re.I)
    provided_body = (body_match.group(1).strip() if body_match else "")

    SetAssistantStatus("Writing email...")
    body = provided_body or draft_email_body(subject=subject, about=about)

    # Show a preview in the chat (voice reads only the status)
    ShowTextToScreen(
        f" {Assistantname} : Draft email\n"
        f"To: {', '.join(recipients)}\n"
        f"Subject: {subject}\n\n"
        f"{body}"
    )
    TextToSpeech("Okay. I drafted the email and I am sending it now.")

    # 4) Send
    SetAssistantStatus("Sending email...")
    ok = []
    failed = []
    for to_addr in recipients:
        res = SendEmailSMTP(to_addr, subject, body)
        if res is True:
            ok.append(to_addr)
        else:
            failed.append((to_addr, res))

    # 5) Report result
    if ok and not failed:
        _speak_and_show("Email sent successfully.")
        return True

    lines = []
    if ok:
        lines.append(f"✅ Sent to: {', '.join(ok)}")
    if failed:
        lines.append("❌ Failed:")
        for to_addr, err in failed:
            lines.append(f"  - {to_addr}: {err}")

    ShowTextToScreen(f" {Assistantname} : " + "\n".join(lines))
    _speak_and_show("I couldn't send the email to everyone. Please check the chat for details.")
    return False
def ShowDefaultChatIfNoChats():
    File = open(r' Data\ChatLog.json', "r", encoding='utf-8')
    if len(File.read())<5:
        with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file:
            file.write("")
        with open(TempDirectoryPath('Responses.data'), 'w', encoding='utf-8') as file:
            file.write(DefaultMessage)

def ReadChatLogJson():
    with open(r'Data\ChatLog.json', 'r', encoding='utf-8') as file: 
        chatlog_data = json.load(file)
    return chatlog_data
def ChatLogIntegration():
    json_data = ReadChatLogJson()
    formatted_chatlog = ""
    for entry in json_data:
        if entry["role"] == "user":
            formatted_chatlog += f"User: {entry['content']}\n"
        elif entry["role"] == "assistant":
            formatted_chatlog += f"Assistant: {entry['content']}\n"
        formatted_chatlog = formatted_chatlog.replace("User", Username +"")
        formatted_chatlog = formatted_chatlog.replace("Assistant", Assistantname + "")
        
    with open(TempDirectoryPath('Database.data'), 'w', encoding='utf-8') as file: file.write(AnswerModifier(formatted_chatlog))
    
def ShowChatsOnGUI():
    File = open(TempDirectoryPath('Database.data'),"r", encoding='utf-8') 
    Data = File.read()
    if len(str(Data))>0:
        lines = Data.split('\n')
        result = '\n'.join(lines) 
        File.close()
        File = open(TempDirectoryPath('Responses.data'),"w", encoding='utf-8') 
        File.write(result)
        File.close()
def InitialExecution():
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    ShowDefaultChatIfNoChats()
    ChatLogIntegration()
    ShowChatsOnGUI()
    InitialExecution()  
    
def MainExecution():
    TaskExecution = False 
    ImageExecution = False 
    ImageGenerationQuery = ""
    SetAssistantStatus("Listening ... ") 
    Query = SpeechRecognition() 
    ShowTextToScreen (f"{Username} : {Query}") 

    # --- Interactive send-email shortcut ---
    # If the user only says "send email" (no recipient/subject), start an interactive flow.
    if _norm_cmd(Query) in {"send email", "send an email"}:
        SendEmailFlow(initial_command=Query)
        return True

    SetAssistantStatus("Thinking ... ") 
    Decision = FirstLayerDMM(Query)
    # --- Handle send-email tasks produced by the decision model ---
    # Example DMM outputs:
    #   - send email to john@x.com about meeting tomorrow
    #   - send email to a@b.com subject report body please send the report
    email_tasks = [t for t in Decision if t.strip().startswith("send email")]
    if email_tasks:
        for t in email_tasks:
            SendEmailFlow(initial_command=t)

    print("")
    print(f"Decision : {Decision}") 
    print("")
    G = any([i for i in Decision if i.startswith("general")])
    R = any([i for i in Decision if i.startswith("realtime")])
    Mearged_query =" and" .join(
        [" ".join(i.split()[1:]) for i in Decision if i.startswith("general") or i.startswith("realtime")]
    )

    for queries in Decision:
        if "generate" in queries:
            ImageGenerationQuery= str(queries) 
            ImageExecution = True
    # Only pass executable automation tasks to Automation() to avoid noisy "No Function Found" logs.
    automation_tasks = [q for q in Decision if any(q.startswith(func) for func in Functions)]
    if automation_tasks and TaskExecution is False:
        run(Automation(automation_tasks))
        TaskExecution = True
    if ImageExecution == True:
        prompt = ImageGenerationQuery.removeprefix("generate image").strip().strip(".")
        with open(r"Frontend\Files\ImageGeneration.data", "w", encoding="utf-8") as file:
            file.write(f"{prompt},True")
            try:
                p1 = subprocess.Popen(
                    [sys.executable, r'Backend\ImageGeneration.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    shell=False
                )
                subprocesses.append(p1)
            except Exception as e:
                print("Error starting ImageGeneration.py: {e}")
    if G and R:
        SetAssistantStatus("Searching...")
        Answer = RealtimeSearchEngine (QueryModifier (Mearged_query)) 
        ShowTextToScreen(f" {Assistantname}:{Answer}")
        SetAssistantStatus("Answering ...")
        TextToSpeech(Answer)
        return True
    else:
        for Queries in Decision:
            if Queries.startswith("general"):
                SetAssistantStatus("Thinking ... ")
                QueryFinal = Queries.removeprefix("general").strip()
                if not QueryFinal:
                    QueryFinal = Query
                print("RAW QueryFinal:", repr(QueryFinal))
                print("MOD Query:", repr(QueryModifier(QueryFinal)))
                Answer = ChatBot(QueryFinal)
                ShowTextToScreen (f" {Assistantname} :{Answer}") 
                SetAssistantStatus("Answering...")
                TextToSpeech(Answer)
                return True
            elif Queries.startswith("realtime"):
                SetAssistantStatus("Searching ... ")
                Answer = RealtimeSearchEngine(Query)
                ShowTextToScreen(f" {Assistantname} {Answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech (Answer)
                return True
            elif "exit" in Queries:
                QueryFinal = "ay, Bye!"
                Answer = ChatBot(QueryFinal)
                ShowTextToScreen(f" {Assistantname} : {Answer}")
                SetAssistantStatus("Answering...")
                TextToSpeech(Answer)
                SetAssistantStatus("Answering ...")
                os._exit(1)
def FirstThread():
    while True:
        CurrentStatus = GetMicrophoneStatus()
        if CurrentStatus == "True":
            MainExecution()
        else:
            AIStatus = GetAssistantStatus()
            if "Available..." in AIStatus: 
                sleep(0.1)
            else:
                SetAssistantStatus("Available...")

def SecondThread():
    GraphicalUserInterface()
if __name__ == "__main__":
    thread2 = threading. Thread(target=FirstThread, daemon=True)
    thread2.start()
    SecondThread()