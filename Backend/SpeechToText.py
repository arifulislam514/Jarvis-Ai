import os
import time
import tempfile
from dotenv import dotenv_values
import mtranslate as mt
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav

try:
    from faster_whisper import WhisperModel
except Exception as e:
    raise RuntimeError(
        "faster-whisper is not installed or failed to import.\n"
        "Run: pip install faster-whisper\n"
        "Also ensure ffmpeg is installed and in PATH."
    ) from e


# =========================
# Env / Paths
# =========================
env_vars = dotenv_values(".env")

STT_MODEL_SIZE = env_vars.get("STT_MODEL_SIZE", "small")       # tiny / base / small / medium / large-v3
STT_DEVICE = env_vars.get("STT_DEVICE", "cpu")                # cpu / cuda
STT_COMPUTE = env_vars.get("STT_COMPUTE", "int8")             # int8 / float16 (cuda) / float32
OUTPUT_LANGUAGE = env_vars.get("OUTPUT_LANGUAGE", "en")        # set "en" to keep your pipeline English
MIC_DEVICE = env_vars.get("MIC_DEVICE", None)                 # optional: device name or index

MAX_RECORD_SECONDS = float(env_vars.get("MAX_RECORD_SECONDS", "10"))
SILENCE_STOP_SECONDS = float(env_vars.get("SILENCE_STOP_SECONDS", "1.0"))
CALIBRATION_SECONDS = float(env_vars.get("CALIBRATION_SECONDS", "0.5"))
SAMPLE_RATE = int(env_vars.get("SAMPLE_RATE", "16000"))

# ✅ NEW: language hint/force + decode quality
# Prefer INPUT_LANGUAGE, but also accept your old InputLanguage key
InputLanguage = (env_vars.get("INPUT_LANGUAGE") or env_vars.get("InputLanguage") or "auto").strip().lower()
STT_BEAM_SIZE = int(env_vars.get("STT_BEAM_SIZE", "5"))

current_dir = os.getcwd()

DATA_DIR = os.path.join(current_dir, "Data")
os.makedirs(DATA_DIR, exist_ok=True)

TempDirPath = os.path.join(current_dir, "Frontend", "Files")
os.makedirs(TempDirPath, exist_ok=True)


# =========================
# Model init (lazy)
# =========================
_model = None

def SetAssistantStatus(Status: str):
    with open(os.path.join(TempDirPath, "Status.data"), "w", encoding="utf-8") as f:
        f.write(Status)

def get_model():
    global _model
    if _model is None:
        SetAssistantStatus("Loading STT model...")
        print("Loading STT model...", flush=True)
        _model = WhisperModel(STT_MODEL_SIZE, device=STT_DEVICE, compute_type=STT_COMPUTE)
        print("STT model loaded.", flush=True)
        SetAssistantStatus("Listening...")
    return _model


# =========================
# Helpers
# =========================
def _safe_write(filename: str, content: str):
    try:
        with open(os.path.join(TempDirPath, filename), "w", encoding="utf-8") as f:
            f.write(content or "")
    except Exception:
        pass


def QueryModifier(Query: str) -> str:
    q = (Query or "").strip()
    if not q:
        return ""

    new_query = q.lower().strip()
    query_words = new_query.split()

    question_starts = [
        "how", "what", "who", "where", "when", "why", "which", "whose", "whom",
        "can you", "could you", "would you",
        "is", "are", "do", "does", "did", "will", "shall", "may", "might"
    ]

    is_question = any(new_query.startswith(w) for w in question_starts)

    last_char = query_words[-1][-1] if query_words and query_words[-1] else ""
    if is_question:
        if last_char in [".", "?", "!"]:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if last_char in [".", "?", "!"]:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."

    return new_query.capitalize()


def _rms_int16(x: np.ndarray) -> float:
    xf = x.astype(np.float32)
    return float(np.sqrt(np.mean(xf * xf)) + 1e-9)


def _resolve_device():
    if MIC_DEVICE is None or str(MIC_DEVICE).strip() == "":
        return None
    try:
        return int(MIC_DEVICE)
    except ValueError:
        return str(MIC_DEVICE)


def _record_until_silence(
    sample_rate: int = SAMPLE_RATE,
    max_seconds: float = MAX_RECORD_SECONDS,
    silence_stop_seconds: float = SILENCE_STOP_SECONDS,
    calibration_seconds: float = CALIBRATION_SECONDS,
):
    device = _resolve_device()
    block_ms = 50
    block_size = int(sample_rate * (block_ms / 1000.0))
    if block_size <= 0:
        block_size = 800

    SetAssistantStatus("Listening...")
    cal_blocks = max(1, int((calibration_seconds * sample_rate) / block_size))
    noise_rms_vals = []

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=block_size,
        device=device
    ) as stream:
        for _ in range(cal_blocks):
            data, _ = stream.read(block_size)
            chunk = np.squeeze(data, axis=-1)
            noise_rms_vals.append(_rms_int16(chunk))

        noise_rms = float(np.median(noise_rms_vals)) if noise_rms_vals else 200.0
        threshold = max(250.0, noise_rms * 3.0 + 150.0)

        frames = []
        started = False
        silent_time = 0.0
        total_time = 0.0

        while total_time < max_seconds:
            data, _ = stream.read(block_size)
            chunk = np.squeeze(data, axis=-1)

            rms = _rms_int16(chunk)
            is_voice = rms >= threshold

            frames.append(chunk)
            total_time += (block_size / sample_rate)

            if is_voice:
                started = True
                silent_time = 0.0
                SetAssistantStatus("Recognizing...")
            else:
                if started:
                    silent_time += (block_size / sample_rate)
                    if silent_time >= silence_stop_seconds:
                        break

    audio = np.concatenate(frames) if frames else np.array([], dtype=np.int16)
    return audio


def _audio_to_temp_wav(audio_int16: np.ndarray, sample_rate: int = SAMPLE_RATE) -> str:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp.close()
    wav.write(tmp.name, sample_rate, audio_int16)
    return tmp.name


def _whisper_transcribe(wav_path: str):
    """
    Returns (raw_text, detected_lang, english_text)
    english_text is produced via mtranslate when OUTPUT_LANGUAGE == 'en'
    """
    m = get_model()

    language_arg = None if InputLanguage in ("auto", "", "none") else InputLanguage

    segments, info = m.transcribe(
        wav_path,
        beam_size=STT_BEAM_SIZE,
        vad_filter=True,
        language=language_arg,
    )

    raw_text = " ".join(seg.text.strip() for seg in segments).strip()
    detected_lang = getattr(info, "language", None) or (language_arg or "unknown")

    if OUTPUT_LANGUAGE.lower() == "en" and detected_lang.lower() != "en" and raw_text:
        SetAssistantStatus("Translating...")
        english_text = mt.translate(raw_text, "en", "auto").strip()
    else:
        english_text = raw_text

    return raw_text, detected_lang, english_text


def SpeechRecognition():
    try:
        audio = _record_until_silence()
        if audio.size == 0:
            SetAssistantStatus("Idle")
            return ""

        wav_path = _audio_to_temp_wav(audio)

        try:
            raw_text, lang, english_text = _whisper_transcribe(wav_path)

            _safe_write("LastLang.data", lang)
            _safe_write("LastRaw.data", raw_text)
            _safe_write("LastEnglish.data", english_text)

            SetAssistantStatus("Idle")
            return QueryModifier(english_text)

        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass

    except Exception as e:
        SetAssistantStatus("Error")
        _safe_write("LastSTTError.data", str(e))
        return ""


if __name__ == "__main__":
    print("Multilingual STT ready. Speak a command...")
    while True:
        text = SpeechRecognition()
        if text:
            lang = ""
            try:
                with open(os.path.join(TempDirPath, "LastLang.data"), "r", encoding="utf-8") as f:
                    lang = f.read().strip()
            except Exception:
                pass

            print(f"[{lang}] {text}")

        time.sleep(0.1)
