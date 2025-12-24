"""
Deterministic real-time helpers (no LLM) for accuracy-sensitive queries.

Why this exists:
- Google snippets + LLM summarization is often wrong for numbers (currency) and live data (weather).
- These helpers call stable JSON APIs and return a clean plain-text answer.

APIs used (no key required):
- Currency: open.er-api.com
- Weather + geocoding: open-meteo.com
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

import requests


# -----------------------------
# Currency
# -----------------------------

_CURRENCY_CODE_RE = re.compile(r"\b([A-Z]{3})\b")


def _parse_currency_query(prompt: str) -> Optional[Tuple[float, str, str]]:
    """Return (amount, base, quote) if prompt looks like a currency conversion."""
    text = (prompt or "").strip()
    if not text:
        return None

    upper = text.upper()

    # Amount (default 1)
    amount = 1.0
    m_amt = re.search(r"\b(\d+(?:\.\d+)?)\b", upper)
    if m_amt:
        try:
            amount = float(m_amt.group(1))
        except Exception:
            amount = 1.0

    # "USD to BDT" / "USD in BDT"
    m = re.search(r"\b([A-Z]{3})\b\s*(?:TO|IN|=|->)\s*\b([A-Z]{3})\b", upper)
    if m:
        base, quote = m.group(1), m.group(2)
        return amount, base, quote

    # If contains keywords: "exchange rate USD BDT"
    codes = _CURRENCY_CODE_RE.findall(upper)
    if len(codes) >= 2 and any(k in upper for k in ("EXCHANGE", "RATE", "CONVERT", "HOW MUCH", "VALUE", "PRICE")):
        return amount, codes[0], codes[1]

    # If user types "USD BDT" only
    if len(codes) == 2 and len(upper.split()) <= 4:
        return amount, codes[0], codes[1]

    return None


def _get_rates(base: str, timeout: float = 10.0) -> dict:
    url = f"https://open.er-api.com/v6/latest/{base}"
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()

    if str(data.get("result")).lower() != "success":
        raise RuntimeError(f"Currency API error: {data.get('error-type') or data}")

    # API returns "rates" (new). Some older implementations used "conversion_rates".
    rates = data.get("rates") or data.get("conversion_rates")
    if not isinstance(rates, dict) or not rates:
        raise RuntimeError("Currency API returned no rates.")

    # Normalize to one key so the rest of code stays stable
    data["rates"] = rates
    return data


def currency_answer(prompt: str) -> Optional[str]:
    parsed = _parse_currency_query(prompt)
    if not parsed:
        return None

    amount, base, quote = parsed
    try:
        data = _get_rates(base)
        rates = data["rates"]
        if quote not in rates:
            return f"I can’t find a rate for {quote}. Use a valid 3-letter code (e.g., USD, EUR, BDT)."

        rate = float(rates[quote])
        converted = amount * rate

        stamp = str(data.get("time_last_update_utc") or "").strip()
        stamp_line = f"\nLast update (UTC): {stamp}" if stamp else ""

        def _fmt(x: float) -> str:
            if x == 0:
                return "0"
            if abs(x) >= 1:
                return f"{x:,.4f}".rstrip("0").rstrip(".")
            return f"{x:.8f}".rstrip("0").rstrip(".")

        return (
            f"{_fmt(amount)} {base} = {_fmt(converted)} {quote}\n"
            f"Rate: 1 {base} = {_fmt(rate)} {quote}{stamp_line}"
        )
    except Exception as e:
        return f"Currency lookup failed: {e}"


# -----------------------------
# Weather
# -----------------------------

def _parse_weather_query(prompt: str) -> Optional[str]:
    text = (prompt or "").strip()
    if not text:
        return None

    lower = text.lower()
    if not any(k in lower for k in ("weather", "temperature", "forecast", "rain", "humidity", "wind")):
        return None

    # "... in <location>"
    m = re.search(r"\b(?:in|at|for)\s+([a-zA-Z][a-zA-Z\s\-\,\.]{1,60})$", text.strip(), flags=re.I)
    if m:
        return m.group(1).strip(" ,.-\t\n")

    # "weather <location>" / "forecast <location>"
    m2 = re.search(r"\b(?:weather|forecast|temperature)\b\s+([a-zA-Z][a-zA-Z\s\-\,\.]{1,60})", text, flags=re.I)
    if m2:
        return m2.group(1).strip(" ,.-\t\n")

    return None


_WEATHER_CODE = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def _geocode(place: str, timeout: float = 10.0) -> Optional[dict]:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": place, "count": 1, "language": "en", "format": "json"}
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    results = data.get("results")
    if isinstance(results, list) and results:
        return results[0]
    return None


def weather_answer(prompt: str) -> Optional[str]:
    place = _parse_weather_query(prompt)
    if not place:
        return None

    try:
        geo = _geocode(place)
        if not geo:
            return f"I couldn’t find a location called '{place}'. Try '{place}, Bangladesh'."

        lat = geo["latitude"]
        lon = geo["longitude"]
        name = geo.get("name") or place
        admin1 = geo.get("admin1")
        country = geo.get("country")
        label = ", ".join([p for p in [name, admin1, country] if p])

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code",
            "forecast_days": 3,
            "timezone": "auto",
        }
        r = requests.get(url, params=params, timeout=10.0)
        r.raise_for_status()
        data = r.json()

        cur = data.get("current") or {}
        temp = cur.get("temperature_2m")
        feels = cur.get("apparent_temperature")
        rh = cur.get("relative_humidity_2m")
        wind = cur.get("wind_speed_10m")
        wcode = cur.get("weather_code")
        wdesc = _WEATHER_CODE.get(int(wcode), "Unknown") if wcode is not None else "Unknown"

        line1 = f"Weather in {label}: {wdesc}."
        line2_parts = []
        if temp is not None:
            line2_parts.append(f"Temp: {temp}°C")
        if feels is not None:
            line2_parts.append(f"Feels like: {feels}°C")
        if rh is not None:
            line2_parts.append(f"Humidity: {rh}%")
        if wind is not None:
            line2_parts.append(f"Wind: {wind} km/h")
        line2 = " | ".join(line2_parts) if line2_parts else ""

        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        pmax = daily.get("precipitation_probability_max") or []
        wcd = daily.get("weather_code") or []

        outlook_lines = []
        for i in range(min(3, len(dates))):
            d = str(dates[i])
            desc = _WEATHER_CODE.get(int(wcd[i]), "Unknown") if i < len(wcd) and wcd[i] is not None else "Unknown"
            hi = f"{tmax[i]}°C" if i < len(tmax) else "?"
            lo = f"{tmin[i]}°C" if i < len(tmin) else "?"
            pr = f"{pmax[i]}%" if i < len(pmax) else "?"
            outlook_lines.append(f"- {d}: {desc}, {lo}–{hi}, precip. chance {pr}")

        updated = ""
        if isinstance(cur.get("time"), str):
            updated = f"\nUpdated local time: {cur['time']}"

        out = line1
        if line2:
            out += "\n" + line2
        if outlook_lines:
            out += "\n\nNext 3 days:\n" + "\n".join(outlook_lines)
        if updated:
            out += updated

        return out
    except Exception as e:
        return f"Weather lookup failed: {e}"


# -----------------------------
# Router
# -----------------------------

def try_handle_realtime(prompt: str) -> Optional[str]:
    """Return an answer if prompt is currency/weather, else None."""
    ans = currency_answer(prompt)
    if ans:
        return ans
    return weather_answer(prompt)
