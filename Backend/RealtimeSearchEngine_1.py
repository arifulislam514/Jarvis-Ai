import requests
from bs4 import BeautifulSoup
import datetime
from dotenv import dotenv_values
from groq import Groq
from json import load, dump
import re
import time

# ----------------------------- #
#  Load Environment Variables
# ----------------------------- #
env_vars = dotenv_values(".env")

Username = env_vars.get("Username", "User")
Assistantname = env_vars.get("Assistantname", "Ciel")
GroqAPIKey = env_vars.get("GroqAPIKey")

client = Groq(api_key=GroqAPIKey)

# ----------------------------- #
#  System Prompt
# ----------------------------- #
System = f"""Hello, I am {Username}, You are {Assistantname}, an advanced AI assistant.
You have real-time access to the internet and can summarize fresh information professionally.
Use correct grammar, punctuation, and provide clear, concise answers.
"""

# ----------------------------- #
#  Utility Functions
# ----------------------------- #
def Information():
    current_date_time = datetime.datetime.now()
    return (
        f"Real-time info:\n"
        f"Date: {current_date_time.strftime('%A, %d %B %Y')}\n"
        f"Time: {current_date_time.strftime('%H:%M:%S')}\n"
    )

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    return '\n'.join(non_empty_lines)

# ----------------------------- #
#  Chat Log Loader
# ----------------------------- #
try:
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)
except:
    messages = []
    with open(r"Data\ChatLog.json", "w") as f:
        dump([], f)

# ----------------------------- #
#  Currency Detection + API
# ----------------------------- #
def detect_currency_query(prompt):
    """
    Detects currency conversion requests robustly:
    works for lowercase, uppercase, and mixed formats.
    Examples it will detect:
    - usd to bdt
    - convert eur to inr
    - 1 gbp in usd
    - 100 usd vs bdt
    """
    text = prompt.upper().strip()
    pattern = r"([A-Z]{3})\s*(?:TO|IN|VS)\s*([A-Z]{3})"
    match = re.search(pattern, text)
    if match:
        base, target = match.groups()
        return base.strip(), target.strip()
    return None



def fetch_currency_rate(base, target):
    """
    Fetch live currency conversion using open.er-api.com
    (Free and works globally without API key)
    """
    try:
        url = f"https://open.er-api.com/v6/latest/{base.upper()}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # API returns result='success' on success
        if data.get("result") != "success":
            return f"⚠️ API did not return success for {base}."

        rates = data.get("rates", {})
        if target.upper() in rates:
            rate = rates[target.upper()]
            return f"💱 As of now, 1 {base.upper()} = {rate:.2f} {target.upper()}."
        else:
            return f"⚠️ Conversion rate from {base} to {target} not found."
    except Exception as e:
        return f"❌ Currency fetch failed: {str(e)}"



# ----------------------------- #
#  DuckDuckGo Web Search
# ----------------------------- #
def search_duckduckgo(query, max_results=5):
    print("🔎 Searching the web...")
    headers = {"User-Agent": "Mozilla/5.0"}
    search_url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
    try:
        res = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        results = []
        for a in soup.select(".result__a")[:max_results]:
            title = a.text
            url = a.get("href")
            if url.startswith("/"):
                continue
            results.append({"title": title, "url": url})
        return results
    except Exception as e:
        print("❌ Search error:", e)
        return []

def fetch_page_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return text[:1500]  # limit to avoid token overload
    except:
        return ""

def summarize_content(text):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Summarize the following text into concise, factual points."},
            {"role": "user", "content": text},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return completion.choices[0].message.content.strip()

# ----------------------------- #
#  Universal Realtime Search Engine
# ----------------------------- #
def RealtimeSearchEngine(prompt):
    global messages

    # Log the user query
    with open(r"Data\ChatLog.json", "r") as f:
        messages = load(f)
    messages.append({"role": "user", "content": prompt})

    # ⚡ 1. Currency Fallback
    currency_pair = detect_currency_query(prompt)
    if currency_pair:
        base, target = currency_pair
        answer = fetch_currency_rate(base, target)
        print("🧠 Using currency API...")
        messages.append({"role": "assistant", "content": answer})
        with open(r"Data\ChatLog.json", "w") as f:
            dump(messages, f, indent=4)
        return answer

    # ⚙️ 2. Web Search
    results = search_duckduckgo(prompt)
    if not results:
        return "I couldn’t find relevant information online."

    combined_text = ""
    for r in results:
        page_text = fetch_page_text(r["url"])
        combined_text += f"{r['title']}\n{page_text}\n\n"
        time.sleep(0.5)

    summarized_info = summarize_content(combined_text)

    print("🧠 Generating final answer with Groq...")
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": System},
            {"role": "system", "content": Information()},
            {"role": "user", "content": f"Question: {prompt}\n\nContext:\n{summarized_info}"},
        ],
        temperature=0.5,
        max_tokens=800,
    )
    Answer = completion.choices[0].message.content.strip()

    messages.append({"role": "assistant", "content": Answer})
    with open(r"Data\ChatLog.json", "w") as f:
        dump(messages, f, indent=4)

    return AnswerModifier(Answer)


# ----------------------------- #
#  Main Loop
# ----------------------------- #
if __name__ == "__main__":
    print(f"{Assistantname} is online. Type 'exit' to quit.\n")
    while True:
        prompt = input("Enter your Query: ")
        if prompt.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        print(RealtimeSearchEngine(prompt))
