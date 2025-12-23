# Import required libraries
from AppOpener import close, open as appopen #Import functions to open and close apps. 
from webbrowser import open as webopen # Import web browser functionality. 
# from pywhatkit import search, playonyt #Import functions for Google search and YouTube playback. 
from dotenv import dotenv_values #Import doteny to manage environment variables. 
from bs4 import BeautifulSoup # Import BeautifulSoup for parsing HTML content. 
from rich import print #Import rich for styled console output. 
from groq import Groq #Import Groq for AI chat functionalities.
import webbrowser # Import webbrowser for opening URLS.
import subprocess # Import subprocess for interacting with the system. 
import requests # Import requests for making HTTP requests.
import keyboard #Import keyboard for keyboard-related actions. 
import asyncio # Import asyncio for asynchronous programming. 
import os
import urllib # Import os for operating system functionalities.
import smtplib
from email.message import EmailMessage

#Load environment variables from the .env file.
env_vars= dotenv_values(".env")
Username = env_vars.get("Username") or env_vars.get("username") or "User"
GroqAPIKey = env_vars.get("GroqAPIKey") # Retrieve the Groq API key.

# Define CSS classes for parsing specific elements in HTML content.
classes = ["zCubwf", "hgKELc", "LTKOO SY7ric", "ZOLcW", "gsrt vk_bk FzvWSb YwPhnf", "pclqee",
"tw-Data-text tw-text-small tw-ta",
"IZ6rdc", "05uR6d LTKOO", "vlzY6d", "webanswers-webanswers_table_webanswers-table",
"dDoNo ikb4Bb gsrt", "sXLa0e",
"LWkfKe", "VQF4g", "qv3Wpe", "kno-rdesc", "SPZz6b"]

# Define a user-agent for making web requests.
useragent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"

# Initialize the Groq client with the API key.
client = Groq(api_key=GroqAPIKey)

# Predefined professiobal responses for user interactions.
professional_responses = [
    "Your satisfaction is my top priority; feel free to reach out if there's anything else I can help you with.",
    "I'm at your service for any additional questions or support you may need-don't hesitate to ask.",
]

#List to store chatbot messages.
messages = []

# System message to provide context to the chatbot.
SystemChatBot = [{"role": "system", "content": f"Hello, I am {Username}, You're a content writer. You have to write content like letters, codes, applications, essays, poems etc."}]

#Function to perform a Google search. 
def GoogleSearch(Topic):
    try:
        from pywhatkit import search
        search(Topic)
        return True
    except Exception as e:
        print(f"[red]GoogleSearch failed (pywhatkit / internet): {e}[/red]")
        # fallback: open browser search page
        import urllib.parse
        url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(Topic)
        webbrowser.open(url)
        return True

# Function to generate content using AI and save it to a file.
def Content (Topic):
    
    #Nested function to open a file in Notepad.
    def OpenNotepad(File):
        default_text_editor = 'notepad.exe' # Default text editor.
        subprocess.Popen([default_text_editor, File]) # Open the file in Notepad.

    # Nested function to generate content using the AI chatbot.
    def ContentWriterAI(prompt):
        messages.append({"role": "user", "content": f" {prompt}"}) # Add the user's prompt to messages. 
    
        completion = client.chat.completions.create(
            model="qwen/qwen3-32b", # Specify the AI model.
            messages=SystemChatBot + messages, # Include system instructions and chat history.
            max_tokens=512, # Limit the maximum tokens in the response.
            temperature=0.7, # Adjust response randomness.
            top_p=1, # Use nucleus sampling for response diversity. 
            stream=True, # Enable streaming response.
            stop=None # Allow the model to determine stopping conditions.
        )
        
        Answer ="" #Initialize an empty string for the response.
        
        #Process streamed response chunks.
        for chunk in completion:
            if chunk.choices[0].delta.content: # Check for content in the current chunk.
                Answer += chunk.choices[0].delta.content #Append the content to the answer.
        
        Answer = Answer.replace("</s>", "") # Remove unwanted tokens from the response. 
        messages.append({"role": "assistant", "content": Answer}) #Add the AI's response to messages.
        return Answer
    
    Topic: str = Topic.replace("Content", "") # Remove "Content" from the topic. 
    ContentByAI = ContentWriterAI (Topic) # Generate content using AI.

    # Save the generated content to a text file.
    filename = os.path.join("Data", f"{Topic.lower().replace(' ', '')}.txt")
    with open(filename, "w", encoding="utf-8") as file:
        file.write(ContentByAI)

    OpenNotepad(filename)  # Open the file in Notepad.
    return True  # Indicate success.

# sending email function
def SendEmailSMTP(to_email: str, subject: str, body: str, cc: str = "", bcc: str = ""):
    """
    Send an email using SMTP settings from .env.
    Returns True on success, or an error string on failure.
    """
    host = env_vars.get("SMTP_HOST")
    port = int(env_vars.get("SMTP_PORT", "587"))
    user = env_vars.get("SMTP_USER")
    password = env_vars.get("SMTP_PASS")
    use_tls = str(env_vars.get("SMTP_USE_TLS", "true")).lower() in ("1", "true", "yes", "y", "on")
    from_addr = env_vars.get("SMTP_FROM") or user

    if not all([host, port, user, password, from_addr]):
        return "SMTP is not configured. Please set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM in .env"

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_email
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject
    msg.set_content(body)

    recipients = [to_email]
    if cc:
        recipients += [x.strip() for x in cc.split(",") if x.strip()]
    if bcc:
        recipients += [x.strip() for x in bcc.split(",") if x.strip()]

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            server.login(user, password)
            server.send_message(msg, from_addr=from_addr, to_addrs=recipients)
        return True
    except Exception as e:
        return f"Email failed: {e}"

# Add a small parser for the command string
# This lets you pass one “email … | subject … | body …” command cleanly:
def parse_email_command(command: str):
    """
    Expected format:
      email to someone@site.com | subject Hello | body This is the message | cc a@x.com,b@y.com | bcc c@z.com
    """
    raw = command.strip()
    # remove leading "email " or "send email "
    raw = raw.removeprefix("send email ").removeprefix("email ").strip()

    parts = [p.strip() for p in raw.split("|") if p.strip()]
    data = {"to": "", "subject": "", "body": "", "cc": "", "bcc": ""}

    for p in parts:
        lower = p.lower()
        if lower.startswith("to "):
            data["to"] = p[3:].strip()
        elif lower.startswith("subject "):
            data["subject"] = p[8:].strip()
        elif lower.startswith("body "):
            data["body"] = p[5:].strip()
        elif lower.startswith("cc "):
            data["cc"] = p[3:].strip()
        elif lower.startswith("bcc "):
            data["bcc"] = p[4:].strip()

    # also support: "to someone@x.com" without the pipe
    if not data["to"] and raw.lower().startswith("to "):
        data["to"] = raw[3:].strip()

    if not data["to"] or not data["subject"] or not data["body"]:
        return None, "Email command needs: to, subject, body. Example: email to a@b.com | subject Hi | body Hello"
    return data, None


#Function to search for a topic on YouTube.
def YouTubeSearch(Topic):
    Url4Search = f"https://www.youtube.com/results?search_query={Topic}" # Construct the YouTube search URL. 
    webbrowser.open(Url4Search) # Open. the search URL in a web browser.
    return True # Indicate success.

#Function to play a video on YouTube.
def PlayYoutube(query):
    try:
        from pywhatkit import playonyt
        playonyt(query)
        return True
    except Exception as e:
        print(f"[red]PlayYoutube failed (pywhatkit / internet): {e}[/red]")
        # fallback: open youtube search page
        import urllib.parse
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
        webbrowser.open(url)
        return True

#Function to open an application or a relevant webpage.
def OpenApp(app, sess=None):
    """
    Try to open an installed app.
    If not installed, DON'T hang — return: "App '<name>' is not available".
    Optionally, you can open a web search page instead.
    """
    if sess is None:
        sess = requests.Session()

    try:
        appopen(app, match_closest=True, output=True, throw_error=True)
        return True

    except Exception:
        # --- quick & safe fallback (NO hanging) ---
        try:
            # Instead of scraping Google HTML (fragile), just open search page quickly
            # (This is optional — remove these 2 lines if you ONLY want the message.)
            q = urllib.parse.quote_plus(app)
            webbrowser.open(f"https://{q}.com")
        except Exception:
            pass

        return f"App '{app}' is not available on this system."
    
#Function to close an application. 
def CloseApp(app):
    if "chrome" in app:
        pass # Skip if the app is Chrome.
    else:
        try:
            close(app, match_closest =True, output=True, throw_error=True) #Attempt to close the app. 
            return True #Indicate success.
        except:
            return False # Indicate failure.

#Function to execute system-level commands. 
def System(command):
    
    # Nested function to mute the system volume.
    def mute():
        keyboard.press_and_release("volume mute") # Simulate the mute key press.
    
    # Nested function to unmute the system volume.
    def unmute():
        keyboard.press_and_release("volume mute") # Simulate the unmute key press.
    
    # Nested function to increase the system volume.
    def volume_up():
        keyboard.press_and_release("volume up") #Simulate the volume up key press.
    
    #Nested function to decrease the system volume. 
    def volume_down():
        keyboard.press_and_release("volume down") # Simulate the volume down key press.
    
    # Execute the appropriate command.
    if command == "mute":
        mute()
    elif command == "unmute":
        unmute()
    elif command == "volume up":
        volume_up()
    elif command == "volume down":
        volume_down()
        
    return True #Indicate success.

# Asynchronous function to translate and execute user commands. 
async def TranslateAndExecute(commands: list[str]):
    
    funcs = [] # List to store asynchronous tasks.
    
    for command in commands:
        
        if command.startswith("open "): # Handle "open" commands.
            
            if "open it" in command: # Ignore "open it" commands. 
                pass
            
            if "open file" == command: #Ignore "open file" commands.
                pass
            
            else:
                fun =asyncio.to_thread(OpenApp, command.removeprefix("open ")) # Schedule app opening.
                funcs.append(fun)
                
        elif command.startswith("general"): # Placeholder for general commands.
            pass
        
        elif command.startswith("realtime "): # Placeholder for real-time commands.
            pass
        
        elif command.startswith("close"): # Handle "close" commands.
            fun = asyncio.to_thread(CloseApp, command.removeprefix("close")) #Schedule app closing.
            funcs.append(fun)
            
        elif command.startswith("play "): #Handle "play" commands.
            fun = asyncio.to_thread (PlayYoutube, command.removeprefix("play ")) # Schedule YouTube playback.
            funcs.append(fun)
            
        elif command.startswith("content"): #Handle "content" commands. 
            fun = asyncio.to_thread (Content, command.removeprefix("content")) #Schedule content creation.
            funcs.append(fun)

        elif command.startswith("google search "): #Handle Google search commands.
            fun = asyncio.to_thread (GoogleSearch, command.removeprefix("google search ")) # Schedule Google search.
            funcs.append(fun)
            
        elif command.startswith("youtube search "): #Handle YouTube search commands.
            fun = asyncio.to_thread (YouTubeSearch, command.removeprefix("youtube search ")) #Schedule YouTube search. 
            funcs.append(fun)
            
        elif command.startswith("system"): # Handle system commands.
            fun = asyncio.to_thread (System, command.removeprefix("system")) # Schedule system command. 
            funcs.append(fun)
        
        elif command.startswith("email ") or command.startswith("send email "):
            data, err = parse_email_command(command)
            if err:
                # return a message string so Automation() prints it
                funcs.append(asyncio.to_thread(lambda: err))
            else:
                fun = asyncio.to_thread(
                    SendEmailSMTP,
                    data["to"],
                    data["subject"],
                    data["body"],
                    data["cc"],
                    data["bcc"],
                )
                funcs.append(fun)
            
        else:
            print(f"No Function Found. For {command}") # Print an error for unrecognized commands.
    
    results = await asyncio.gather(*funcs) #Execute all tasks concurrently.
    
    for result in results: # Process the results.
        if isinstance(result, str):
            yield result
        else:
            yield result
            
# Asynchronous function to autonate command execution. 
async def Automation(commands: list[str]):
    async for result in TranslateAndExecute(commands):
        if isinstance(result, str):
            print(result)          # <--- now you will see "App 'x' is not available"
    return True

if __name__ == "__main__":
    asyncio.run(Automation([
        "email to test@example.com | subject Test Email | body Hello from my automation!"
    ]))

