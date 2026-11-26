import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "poller_state.json"

SKIP_SENDER_HINTS = ()

def load_history_id() -> str | None:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text()).get("history_id")
    return None

def save_history_id(history_id: str) -> None:
    STATE_PATH.write_text(json.dumps({"history_id": history_id}))

def current_history_id(service) -> str:
    return service.users().getProfile(userId="me").execute()["historyId"]

def my_address(service) -> str:
    return service.users().getProfile(userId="me").execute()["emailAddress"].lower()

def get_new_message_ids(service, start_history_id: str) -> tuple[list[str], str]:
    ids = []
    page_token = None   # Tracks pagination when Gmail returns multiple pages
    latest = start_history_id   # Stores the latest history ID returned by Gmail

    while True:
        # Request gmail history
        response = service.users().history().list(
            userId="me",
            startHistoryId=start_history_id,
            historyTypes=["messageAdded"],
            labelId="INBOX",
            pageToken=page_token,
        ).execute()

        for h in response.get("history", []):
            for added in h.get("messagesAdded", []):
                ids.append(added["message"]["id"])

        latest = response.get("historyId", latest)
        page_token = response.get("nextPageToken")
        if not page_token:
            # Continue looping until Gmail has no more pages
            break

    # Remove duplicate IDs and return
    return list(dict.fromkeys(ids)), latest

def should_skip(email, my_addr: str) -> bool:
    sender = email.sender.lower()
    if my_addr in sender:                       # our own replies
        return True
    return any(hint in sender for hint in SKIP_SENDER_HINTS)