from googlesearch import search
from groq import Groq #Importing the Groq library to use its API.
from json import load, dump #Importing functions to read and write JSON files.
import datetime #Importing the datetime nodule for real-time date and time information.
from dotenv import dotenv_values #Importing dotenv values to read environment variables from a env file.
from groq import APIError
import time
import re
import os

# Load environment variables from the .env file.
env_vars = dotenv_values(".env")

#Retrieve environment variables for the chatbot configuration.
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")

# Initialize the Groq client with the provided API key. Groq(api_key-GroqAPIKey)
client = Groq(api_key=GroqAPIKey)

CHATLOG_PATH = os.path.join("Data", "ChatLog.json")

# Define the system instructions for the chatbot.
System = f"""Hello, I am {Username}, You are a very accurate and advanced AI chatbot named {Assistantname} which has real-time up-to-date information from the internet.
*** Provide Answers In a Professional Way, make sure to add full stops, commas, question marks, and use proper grammar.***
*** Just answer the question from the provided data in a professional way. ***"""

#Try to load the chat log from a JSON file, or create an empty one if it doesn't exist.
try:
    with open(CHATLOG_PATH, "r") as f:
        messages = load(f)
except:
    with open(CHATLOG_PATH, "w") as f:
        dump([], f)
    
# Function to perform a Google search and format the results.
def GoogleSearch(query):
    results = list (search (query, advanced=True, num_results=5))
    Answer = f"The search results for '{query}' are:\n[start]\n"
    
    for i in results:
        Answer += f"Title: {i.title}\nDescription: {i.description}\n\n"
    
    Answer += "[end]"
    return Answer
    
#Function to clean up the answer by removing empty lines.
def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer
    
#Predefined chatbot conversation system message and an initial user message.
SystemChatBot = [
    {"role": "system", "content": System},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can I help you?"}
]

#Function to get real-time information like the corrent date and time.
def Information():
    data = ""
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")
    data += f"Use This Real-time Information if needed:\n"
    data += f"Day: {day}\n"
    data += f"Date: {date}\n"
    data += f"Month: {month}\n"
    data += f"Year: {year}\n"
    data += f"Time: {hour} hours, {minute} minutes, (second) seconds.\n"
    return data
    
#Function to handle real-time search and response generation.
def RealtimeSearchEngine(prompt):
    global SystemChatBot, messages
    
    #Load the chat log from the JSON file.
    with open(CHATLOG_PATH, "r") as f:
        messages = load(f)
    messages.append({"role": "user", "content": f"{prompt}"})
    
    #Add Google search results to the system chatbot messages.
    SystemChatBot.append({"role": "system", "content": GoogleSearch(prompt)})

    # Generate a response using the brog client.
    def _retry_seconds(err: str) -> float:
        m = re.search(r"try again in\s+((\d+)m)?([\d.]+)s", err, re.I)
        if not m:
            return 2.0
        mins = float(m.group(2) or 0)
        secs = float(m.group(3) or 0)
        return mins * 60 + secs
    
    try:
        completion = client.chat.completions.create(
            model="groq/compound-mini",
            messages=SystemChatBot + [{"role": "system", "content": Information()}] + messages,
            temperature=0.7,
            max_tokens=512,
            top_p=1,
            stream=True,
        )
    except APIError as e:
        if "rate_limit" in str(e).lower():
            time.sleep(min(_retry_seconds(str(e)), 10))
            return "I'm temporarily rate-limited. Please try again."
        raise

    Answer = ""


    #Concatenate response chunks from the streaming output.
    for chunk in completion:
        if chunk.choices[0].delta.content:
            Answer +=chunk.choices[0].delta.content
        
    # Clean up the response.
    Answer = Answer.strip().replace("</s>", "")
    messages.append({"role": "assistant", "content": Answer})

    # Save the updated chat log back to the JSON file.
    with open(CHATLOG_PATH, "w") as f:
        dump(messages, f, indent=4)
            
    # Remove the most recent system message from the chatbot conversation.
    SystemChatBot.pop()
    return AnswerModifier(Answer=Answer)

#main entry point of the program for interactive uerying.
if __name__ == "__main__":
    while True:
        prompt = input("Enter your query: ")
        print(RealtimeSearchEngine(prompt))
