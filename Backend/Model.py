import cohere
from rich import print
from dotenv import dotenv_values
from Backend.Automation import SendEmailSMTP
import json
import re
import smtplib
from email.message import EmailMessage

# Load env variables
env_vars = dotenv_values(".env")
api_key = env_vars.get("Cohere_API_KEY")

if not api_key:
    raise ValueError("❌ No API key found. Make sure .env has Cohere_API_KEY=your_key")

# Initialize Cohere client
co = cohere.Client(api_key=api_key)

def SendEmailSMTP(to_email: str, subject: str, body: str):
    host = env_vars.get("SMTP_HOST")
    port = int(env_vars.get("SMTP_PORT", "587"))
    user = env_vars.get("SMTP_USER")
    password = env_vars.get("SMTP_PASS")
    use_tls = str(env_vars.get("SMTP_USE_TLS", "true")).lower() in ("1", "true", "yes", "y", "on")
    from_addr = env_vars.get("SMTP_FROM") or user

    if not all([host, port, user, password, from_addr]):
        return "SMTP not configured. Set SMTP_HOST/PORT/USER/PASS/FROM in .env"

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        return f"Email failed: {e}"




funcs_more = [
    "exit", "general", "realtime", "open", "close", "play", "generate image", "system", "content",
    "google search", "youtube search", "wikipedia search", "news search", "weather", "joke",
    "quote", "fact", "advice", "horoscope", "trivia", "maths", "translate", "define", "synonym",
    "antonym", "spell check", "grammar check", "summarize", "paraphrase", "analyze sentiment",
    "classify text", "extract keywords", "extract entities", "convert text to speech",
    "convert speech to text", "set reminder", "set alarm", "create event", "send email",
    "send message", "make call", "search web", "browse website", "open app", "close app",
    "lock screen", "shutdown", "restart", "sleep", "hibernate", "log out", "take screenshot",
    "record screen", "open file", "close file", "read file", "write file", "delete file",
    "move file", "copy file", "rename file", "compress file", "decompress file", "upload file",
    "download file", "list files", "search files", "create folder", "delete folder", "move folder",
    "copy folder", "rename folder", "list folders", "search folders", "get system info",
    "get network info", "get battery status", "get cpu usage", "get memory usage", "get disk usage",
    "get running processes", "kill process", "start process", "stop process", "restart process",
    "update software", "install software", "uninstall software", "check for updates", "backup data",
    "restore data", "clean up disk", "defragment disk", "optimize system", "monitor system",
    "manage users", "manage permissions", "manage services", "manage startup programs",
    "manage scheduled tasks", "manage firewall", "manage antivirus", "manage updates",
    "manage backups", "manage network", "manage bluetooth", "manage printers", "manage displays",
    "manage audio", "manage power settings", "manage accessibility", "manage privacy settings",
    "manage security settings", "manage notifications", "manage location settings",
    "manage accounts", "manage sync settings", "manage storage settings", "manage app settings",
    "manage system settings", "get help", "get support", "get documentation", "get tutorials",
    "get examples", "get tips", "get tricks", "get best practices", "get troubleshooting steps",
    "get faq", "get community support", "get professional support", "get feedback", "report bug",
    "request feature", "suggest improvement"
]

funcs = [
    "exit", "general", "realtime", "open", "close", "play", "generate image",
    "system", "content", "google search", "youtube search", "reminder","send email"
]

messages = []


preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date information like if the query is 'who was akbar?' respond with 'general who was akbar?', if the query is 'how can i study more effectively?' respond with 'general how can i study more effectively?', if the query is 'can you help me with this math problem?' respond with 'general can you help me with this math problem?', if the query is 'Thanks, i really liked it.' respond with 'general thanks, i really liked it.' , if the query is 'what is python programming language?' respond with 'general what is python programming language?', etc. Respond with 'general (query)' if a query doesn't have a proper noun or is incomplete like if the query is 'who is he?' respond with 'general who is he?', if the query is 'what's his networth?' respond with 'general what's his networth?', if the query is 'tell me more about him.' respond with 'general tell me more about him.', and so on even if it require up-to-date information to answer. Respond with 'general (query)' if the query is asking about time, day, date, month, year, etc like if the query is 'what's the time?' respond with 'general what's the time?'.
-> Respond with 'realtime ( query )' if a query can not be answered by a llm model (because they don't have realtime data) and requires up to date information like if the query is 'who is indian prime minister' respond with 'realtime who is indian prime minister', if the query is 'tell me about facebook's recent update.' respond with 'realtime tell me about facebook's recent update.', if the query is 'tell me news about coronavirus.' respond with 'realtime tell me news about coronavirus.', etc and if the query is asking about any individual or thing like if the query is 'who is akshay kumar' respond with 'realtime who is akshay kumar', if the query is 'what is today's news?' respond with 'realtime what is today's news?', if the query is 'what is today's headline?' respond with 'realtime what is today's headline?', etc.
-> Respond with 'open (application name or website name)' if a query is asking to open any application like 'open facebook', 'open telegram', etc. but if the query is asking to open multiple applications, respond with 'open 1st application name, open 2nd application name' and so on.
-> Respond with 'close (application name)' if a query is asking to close any application like 'close notepad', 'close facebook', etc. but if the query is asking to close multiple applications or websites, respond with 'close 1st application name, close 2nd application name' and so on.
-> Respond with 'play (song name)' if a query is asking to play any song like 'play afsanay by ys', 'play let her go', etc. but if the query is asking to play multiple songs, respond with 'play 1st song name, play 2nd song name' and so on.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate a image with given prompt like 'generate image of a lion', 'generate image of a cat', etc. but if the query is asking to generate multiple images, respond with 'generate image 1st image prompt, generate image 2nd image prompt' and so on.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder like 'set a reminder at 9:00pm on 25th june for my business meeting.' respond with 'reminder 9:00pm 25th june business meeting'.
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down , etc. but if the query is asking to do multiple tasks, respond with 'system 1st task, system 2nd task', etc.
-> Respond with 'content (topic)' if a query is asking to write any type of content like application, codes, emails or anything else about a specific topic but if the query is asking to write multiple types of content, respond with 'content 1st topic, content 2nd topic' and so on.
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on google but if the query is asking to search multiple topics on google, respond with 'google search 1st topic, google search 2nd topic' and so on.
-> Respond with 'youtube search (topic)' if a query is asking to search a specific topic on youtube but if the query is asking to search multiple topics on youtube, respond with 'youtube search 1st topic, youtube search 2nd topic' and so on.
-> Respond with 'send email to <email> subject <subject> body <body>' if a query is asking to send an email. Example: 'send an email to abc@gmail.com with subject Meeting and body We meet at 5pm' Respond: 'send email to abc@gmail.com subject Meeting body We meet at 5pm' If multiple emails: use semicolon (;) not comma: 'to a@x.com;b@y.com' IMPORTANT: Do not use commas inside subject/body. Use spaces or semicolons instead. If multiple tasks,
-> If the user wants to SEND an email, respond with: 'send email to <email> about <what the email should say>' Example: 'Send a greeting email to abc@gmail.com' Respond: 'send email to abc@gmail.com about greeting email friendly tone' IMPORTANT: Output commands in lowercase (send email, content, open, close, etc.).
*** write each task on a new line. Do NOT separate tasks by commas.***
*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye Ciel.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""

ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "do you like pizza?"},
    {"role": "Chatbot", "message": "general do you like pizza?"},
    {"role": "User", "message": "open edge and tell me about banladesh."},
    {"role": "Chatbot", "message": "open edge, general tell me about banladesh."},
    {"role": "User", "message": "open edge open youtube"},
    {"role": "Chatbot", "message": "open edge, open youtube"},
    {"role": "User", "message": "what is today's date and by the way remind me that i have a programing contest on 20th september 11:00am."},
    {"role": "Chatbot", "message": "general what is today's date, reminder 11:00am 20th september programing contest."},
    {"role": "User", "message": "chat with me."},
    {"role": "Chatbot", "message": "general chat with me."},
    {"role": "User", "message": "send an email to test@gmail.com subject hi body how are you"},
    {"role": "Chatbot", "message": "send email to test@gmail.com subject hi body how are you"},
    {"role": "User", "message": "open chrome and send email to a@b.com subject report body send the latest report"},
    {"role": "Chatbot", "message": "open chrome, send email to a@b.com subject report body send the latest report"},
    {"role": "User", "message": "email john@x.com and mary@y.com subject meeting body tomorrow 9am"},
    {"role": "Chatbot", "message": "send email to john@x.com;mary@y.com subject meeting body tomorrow 9am"},
    {"role": "User", "message": "show me a supercar image"},
    {"role": "Chatbot", "message": "generate image supercar"},
]

EMAIL_PREAMBLE = """
You are an expert email writer.
Write clear, well-formatted emails.

Output MUST be valid JSON only (no markdown, no extra text):
{
  "subject": "...",
  "body": "..."
}

Body rules:
- Plain text only with line breaks.
- Greeting, 2–6 short paragraphs, closing + signature placeholder: "Best regards,\\n<YOUR_NAME>"
- Do not invent personal facts.
"""

EMAIL_FEWSHOTS = [
    {"role": "User", "message": "Draft a friendly greeting email to a colleague."},
    {"role": "Chatbot", "message": '{"subject":"Hello! Hope you’re doing well","body":"Hi there,\\n\\nJust wanted to send a quick note to say hello. I hope your week is going smoothly.\\n\\nIf you’re free sometime soon, I’d love to catch up.\\n\\nBest regards,\\n<YOUR_NAME>"}'},

    {"role": "User", "message": "Write a formal email requesting a meeting about project status."},
    {"role": "Chatbot", "message": '{"subject":"Request for Project Status Meeting","body":"Dear <RECIPIENT_NAME>,\\n\\nI hope you are doing well. I would like to schedule a short meeting to review the current status of the project and align on next steps.\\n\\nPlease share your availability this week, and I will send a calendar invite accordingly.\\n\\nSincerely,\\n<YOUR_NAME>"}'}
]


# Pick latest available model
PREFERRED_MODEL = "command-a-03-2025"
FALLBACK_MODELS = ["command", "command-light"]


def FirstLayerDMM(prompt: str = "test"):
    messages.append({"role": "user", "content": f"{prompt}"})

    try:
        stream = co.chat_stream(
            model=PREFERRED_MODEL,
            message=prompt,
            temperature=0.7,
            chat_history=ChatHistory,
            prompt_truncation='OFF',
            connectors=[],
            preamble=preamble,
        )
    except cohere.errors.NotFoundError:
        print(f"[yellow] Model {PREFERRED_MODEL} not found, trying fallback...[/yellow]")
        for fallback in FALLBACK_MODELS:
            try:
                stream = co.chat_stream(
                    model=fallback,
                    message=prompt,
                    temperature=0.7,
                    chat_history=ChatHistory,
                    prompt_truncation='OFF',
                    connectors=[],
                    preamble=preamble,
                )
                break
            except cohere.errors.NotFoundError:
                continue
        else:
            raise RuntimeError("No valid Cohere model available!")

    response = ""
    for event in stream:
        if event.event_type == "text-generation":
            response += event.text

    response = response.replace("\r", "")
    response = [line.strip() for line in response.split("\n") if line.strip()]

    temp = []
    for task in response:
        for func in funcs:
            if task.startswith(func):
                temp.append(task)

    response = temp

    if "(query)" in response:
        newresponse = FirstLayerDMM(prompt=prompt)
        return newresponse
    else:
        return response

def ContentWriterAI_Email(instruction: str) -> dict:
    """
    Returns {"subject": "...", "body": "..."} as dict.
    """
    resp = co.chat(
        model=PREFERRED_MODEL,
        message=instruction,
        temperature=0.6,
        chat_history=EMAIL_FEWSHOTS,
        preamble=EMAIL_PREAMBLE,
        prompt_truncation="OFF",
    )

    text = (resp.text or "").strip()

    # best-effort JSON extraction
    try:
        start = text.find("{")
        end = text.rfind("}")
        data = json.loads(text[start:end+1])
        if "subject" in data and "body" in data:
            return {"subject": str(data["subject"]).strip(), "body": str(data["body"]).strip()}
    except Exception:
        pass

    # fallback
    return {
        "subject": "Message",
        "body": f"Hello,\n\n{instruction}\n\nBest regards,\n<YOUR_NAME>"
    }
    
def parse_send_email_intent(cmd: str):
    """
    Accept: 'send email to a@b.com about <instruction>'
    Returns (recipients, instruction)
    """
    cmd = cmd.strip()
    m = re.search(r"\bsend email\b.*?\bto\b\s+(.+?)(?:\s+\babout\b\s+(.+))?$", cmd, flags=re.I)
    if not m:
        return None

    to_part = (m.group(1) or "").strip()
    instruction = (m.group(2) or "").strip()

    recipients = [x.strip() for x in re.split(r"[;,]", to_part) if x.strip()]
    recipients = [r for r in recipients if "@" in r]

    if not recipients:
        return None
    if not instruction:
        instruction = "Write a polite email based on the user's request."

    return recipients, instruction


def DraftThenSendEmail(cmd: str):
    parsed = parse_send_email_intent(cmd)
    if not parsed:
        return "Invalid format. Use: send email to someone@x.com about <what to write>"

    recipients, instruction = parsed

    draft = ContentWriterAI_Email(instruction)
    subject = draft["subject"]
    body = draft["body"]

    results = []
    for r in recipients:
        res = SendEmailSMTP(r, subject, body)
        results.append((r, res))

    ok = [r for r, res in results if res is True]
    bad = [(r, res) for r, res in results if res is not True]

    out = []
    if ok:
        out.append(f"✅ Sent to: {', '.join(ok)}")
    if bad:
        out.append("❌ Failed:")
        for r, err in bad:
            out.append(f"  - {r}: {err}")
    return "\n".join(out)

def parse_send_email(cmd: str):
    cmd = cmd.strip()

    if not cmd.startswith("send email"):
        return None

    def grab(after_key, before_key=None):
        start = cmd.find(after_key)
        if start == -1:
            return ""
        start += len(after_key)
        if before_key:
            end = cmd.find(before_key, start)
            return cmd[start:end].strip() if end != -1 else cmd[start:].strip()
        return cmd[start:].strip()

    to_part = grab("to ", " subject ")
    subject = grab("subject ", " body ")
    body = grab("body ")

    recipients = [x.strip() for x in to_part.split(";") if x.strip()]

    if not recipients or not subject or not body:
        return None

    return recipients, subject, body
    
if __name__ == "__main__":
    while True:
        user_text = input(">>> ")
        tasks = FirstLayerDMM(user_text)

        print("[green]Decision:[/green]", tasks)

        for t in tasks:
            t = t.strip()

            if t.startswith("send email"):
                print(DraftThenSendEmail(t))

            elif t.startswith("content"):
                # Your existing content writing flow (if any)
                print("[yellow]Content requested:[/yellow]", t)

            else:
                print("[cyan]Other task:[/cyan]", t)

