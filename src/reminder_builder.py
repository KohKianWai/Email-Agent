import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from .state import Email, ReminderDetails

TZ = ZoneInfo("Asia/Kuala_Lumpur")

def generate_event_id(email_id: str) -> str:
    # prevent duplicate calendar events
    return "mail" + hashlib.sha1(email_id.encode()).hexdigest()

def build_reminder_event(email: Email, r: ReminderDetails) -> dict:
    description = (
        f"{(r.description or '').strip()[:500]}\n\n"
        f"From: {email.sender}\n"
        f"Subject: {email.subject}"
    ).strip()

    event = {
        "id": generate_event_id(email.id),
        "summary": f"Reminder: {r.title[:150]}",
        "description": description,
    }

    if r.due_time:
        start = datetime.strptime(f"{r.due_date} {r.due_time}", "%Y-%m-%d %H:%M")
        start = start.replace(tzinfo=TZ)
        end = start + timedelta(minutes=15)
        event["start"] = {"dateTime": start.isoformat(), "timeZone": TZ.key}
        event["end"] = {"dateTime": end.isoformat(), "timeZone": TZ.key}
        popups = [{"method": "popup", "minutes": 10}]

    else:
        day = datetime.strptime(r.due_date, "%Y-%m-%d").date()
        event["start"] = {"date": day.isoformat()}
        event["end"] = {"date": (day + timedelta(days=1)).isoformat()}
        popups = [{"method": "popup", "minutes": 900}]

    event["reminders"] = {"useDefault": False, "overrides": popups}
    return event