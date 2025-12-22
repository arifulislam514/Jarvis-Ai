"""Email drafting + parsing helpers.

This project uses voice + GUI, but the email helpers should stay independent
from UI. The UI layer (Main.py / GUI) can:

1) Ask for recipient email(s) + subject.
2) Call :func:`draft_email_body` to generate a structured email body.
3) Send using SMTP (see Backend/Automation.SendEmailSMTP).
"""

from __future__ import annotations

import re
from typing import List, Optional

from dotenv import dotenv_values

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None  # type: ignore


_ENV = dotenv_values(".env")
_GROQ_KEY = _ENV.get("GroqAPIKey")


EMAIL_SYSTEM_PROMPT = (
    "You are an expert email writer. "
    "Write clear, professional, well-structured plain-text emails.\n\n"
    "Rules:\n"
    "- Output ONLY the email BODY (no JSON, no markdown).\n"
    "- Include: greeting, 2–6 short paragraphs, closing, and signature placeholder\n"
    "  exactly as: Best regards,\\n<YOUR_NAME>\n"
    "- Do not invent personal facts.\n"
    "- Keep it concise, but complete."
)


_EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


def _normalize_spoken_email_text(text: str) -> str:
    """Best-effort normalization for speech-to-text email inputs."""
    t = (text or "").strip().lower()
    # common speech patterns
    t = re.sub(r"\s+at\s+", "@", t)
    t = re.sub(r"\s+dot\s+", ".", t)
    t = re.sub(r"\s+underscore\s+", "_", t)
    t = t.replace("(at)", "@").replace("[at]", "@").replace("{at}", "@")
    t = t.replace("(dot)", ".").replace("[dot]", ".").replace("{dot}", ".")
    # remove spaces around @ and . to help regex
    t = re.sub(r"\s*@\s*", "@", t)
    t = re.sub(r"\s*\.\s*", ".", t)
    # strip trailing punctuation that SpeechRecognition often adds
    t = re.sub(r"[\s\.,;:!\?]+$", "", t)
    return t


def extract_emails(text: str) -> List[str]:
    """Extract 1+ email addresses from free-form text."""
    if not text:
        return []
    t = _normalize_spoken_email_text(text)
    emails = _EMAIL_REGEX.findall(t)
    # dedupe while preserving order
    seen = set()
    out: List[str] = []
    for e in emails:
        if e not in seen:
            out.append(e)
            seen.add(e)
    return out


def clean_subject(subject: str) -> str:
    """Remove trailing punctuation added by the STT QueryModifier."""
    s = (subject or "").strip()
    s = re.sub(r"[\s\.,;:!\?]+$", "", s).strip()
    return s


def maybe_extract_subject(text: str) -> str:
    """Extract a subject from a command like: '... subject <X> body <Y>'."""
    if not text:
        return ""
    m = re.search(r"\bsubject\b\s+(.*)", text, flags=re.I)
    if not m:
        return ""
    subj = m.group(1)
    # stop at body/about if present
    subj = re.split(r"\b(body|about)\b", subj, maxsplit=1, flags=re.I)[0]
    return clean_subject(subj)


def maybe_extract_about(text: str) -> str:
    """Extract an 'about' clause from a command like: 'send email ... about <X>'."""
    if not text:
        return ""
    m = re.search(r"\babout\b\s+(.*)$", text, flags=re.I)
    return (m.group(1).strip() if m else "")


def draft_email_body(
    subject: str,
    about: str = "",
    tone: str = "professional",
    model: str = "llama-3.1-8b-instant",
    max_tokens: int = 450,
) -> str:
    """Draft a plain-text email body.

    Uses Groq if configured; otherwise returns a safe template.
    """
    subject = clean_subject(subject)
    about = (about or "").strip()

    # Fallback draft (no model or missing key)
    def _fallback() -> str:
        lines = [
            "Hello,",
            "",
            f"I hope you're doing well. I'm writing regarding {subject or 'the matter below'}.",
        ]
        if about:
            lines += ["", about]
        lines += [
            "",
            "Please let me know the next steps or if you need anything else from me.",
            "",
            "Best regards,",
            "<YOUR_NAME>",
        ]
        return "\n".join(lines)

    if not _GROQ_KEY or Groq is None:
        return _fallback()

    try:
        client = Groq(api_key=_GROQ_KEY)
        prompt = (
            f"Subject: {subject}\n"
            f"Tone: {tone}\n"
            f"Context (optional): {about or '(none)'}\n\n"
            "Write the email body."
        )
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            top_p=1,
            max_tokens=max_tokens,
            stream=False,
        )

        body = (completion.choices[0].message.content or "").strip()
        # Ensure signature placeholder exists
        if "<YOUR_NAME>" not in body:
            body = body.rstrip() + "\n\nBest regards,\n<YOUR_NAME>"
        return body
    except Exception:
        return _fallback()
