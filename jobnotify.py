#!/usr/bin/env python3
"""
daily_jobs_google.py
- Query Google Custom Search API for entry-level Cloud/DevOps (AWS) roles
- Filter & deduplicate results
- Save CSV and send as email attachment
"""

import os
import requests
import csv
import smtplib
from email.message import EmailMessage
from datetime import datetime

# --- Configuration (set as environment variables) ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # required
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")    # required
RECIPIENT = os.getenv("RECIPIENT_EMAIL")      # required
FROM_EMAIL = os.getenv("SMTP_USER")           # SMTP username / from address
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_PASS = os.getenv("SMTP_PASS")

# Query settings
QUERIES = [
    '("entry-level" OR junior OR fresher) (cloud OR devops OR aws) jobs Chennai',
    '("cloud engineer" OR "devops engineer") (jobs OR hiring) ("Bengaluru" OR "Chennai" OR "Hyderabad")',
    '("entry-level" OR junior) ("Cloud Engineer" OR "SRE")',
]
MAX_RESULTS = 10  # Google Custom Search allows up to 10 per request

# --- Helpers ---
def google_search(query, start=1):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "start": start,
        "gl": "in"
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()

def extract_results(search_json):
    results = []
    for item in search_json.get("items", []):
        results.append({
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet"),
        })
    return results

def dedupe(results):
    seen, out = set(), []
    for r in results:
        key = r.get("url")
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out

# --- Email & File ---
def save_csv(results, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title","url","snippet"])
        writer.writeheader()
        for r in results:
            writer.writerow(r)

def send_email(subject, body, attachment_path=None):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = RECIPIENT
    msg.set_content(body)

    if attachment_path:
        with open(attachment_path, "rb") as f:
            data = f.read()
        msg.add_attachment(data, maintype="application", subtype="csv", filename=os.path.basename(attachment_path))

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        s.login(FROM_EMAIL, SMTP_PASS)
        s.send_message(msg)

# --- Main flow ---
def main():
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID or not RECIPIENT or not FROM_EMAIL or not SMTP_PASS:
        raise SystemExit("Missing required environment variables: GOOGLE_API_KEY, GOOGLE_CSE_ID, RECIPIENT_EMAIL, SMTP_USER, SMTP_PASS")

    all_results = []
    for q in QUERIES:
        try:
            data = google_search(q)
            res = extract_results(data)
            all_results.extend(res)
        except Exception as e:
            print("Search error:", e)

    results = dedupe(all_results)

    if not results:
        body = f"No results found on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        send_email("Daily Jobs Report — No Results", body)
        return

    csvfile = "daily_jobs_google.csv"
    save_csv(results, csvfile)

    top_lines = []
    for i, r in enumerate(results[:10], start=1):
        top_lines.append(f"{i}. {r.get('title')}\n   {r.get('url')}\n   {r.get('snippet')}\n")

    body = "Daily Jobs Report — Entry-level Cloud/DevOps (AWS)\n\n" + "\n".join(top_lines)
    subject = f"Daily Jobs Report — {datetime.utcnow().strftime('%Y-%m-%d')} (Google Search)"
    send_email(subject, body, attachment_path=csvfile)
    print("Report sent.")

if __name__ == "__main__":
    main()
