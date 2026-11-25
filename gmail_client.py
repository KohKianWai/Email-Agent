from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.state import Email
from googleapiclient.errors import HttpError
from pathlib import Path
from bs4 import BeautifulSoup
import os
import base64


BASE_DIR = Path(__file__).resolve().parent
TOKEN_PATH = BASE_DIR / "token.json"
CREDS_PATH = BASE_DIR / "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",  
    "https://www.googleapis.com/auth/calendar.events",
]

def get_credentials() -> Credentials:
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds

def create_gmail_service():
    return build("gmail", "v1", credentials=get_credentials())

def create_calendar_service():
    return build("calendar", "v3", credentials=get_credentials())

# ======== Parsing =========


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # Remove content that is never visible text
    for tag in soup(["script", "style", "head", "title", "meta", "noscript"]):
        tag.decompose()

    # Keep links visible
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        if text and a["href"].startswith("http") and text != a["href"]:
            a.replace_with(f"{text} ({a['href']})")

    text = soup.get_text(separator="\n")

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    text = "\n".join(line for line in lines if line)
    return text

def decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")

def find_part(payload: dict, mime_type: str) -> str | None:
    """Recursively search the MIME tree for the first part of a given type."""
    if payload.get("mimeType") == mime_type and payload.get("body", {}).get("data"):
        return decode(payload["body"]["data"])
    for part in payload.get("parts", []) or []:
        found = find_part(part, mime_type)
        if found:
            return found
    return None

def extract_body(payload: dict) -> str:
    text = find_part(payload, "text/plain")
    if not text:
        html = find_part(payload, "text/html")
        text = html_to_text(html) if html else ""
    return text.strip()

def parse_message(msg: dict) -> Email:
    payload = msg["payload"]
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    return Email(
        id=msg["id"],
        thread_id=msg["threadId"],
        sender=headers.get("from", ""),
        subject=headers.get("subject", "(no subject)"),
        body=extract_body(payload),
        received_at=headers.get("date", ""),
        message_id_header=headers.get("message-id"),
        references=headers.get("references"),
        reply_to=headers.get("reply-to"),
    )

# ======== Fetching =========

def get_email(service, message_id: str) -> Email:
    msg = service.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    return parse_message(msg)

def fetch_emails(
    service,
    max_results: int = 5,
    query: str = "in:inbox -from:me",
) -> list[Email]:
    resp = service.users().messages().list(
        userId="me", maxResults=max_results, q=query
    ).execute()
    return [get_email(service, m["id"]) for m in resp.get("messages", [])]


if __name__ == "__main__":
    gmail = create_gmail_service()
    for e in fetch_emails(gmail, max_results=5):
        print("\n----------------------")
        print(f"From:    {e.sender}")
        print(f"Subject: {e.subject}")
        print(f"Date:    {e.received_at}")
        print(f"Body:    {e.body[:200]}")