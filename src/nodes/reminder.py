from state import EmailState
from langchain_core.runnables import RunnableConfig
from reminder_builder import build_reminder_event
from googleapiclient.errors import HttpError

def create_reminder(state: EmailState, config: RunnableConfig) -> EmailState:
    email = state["email"]
    r = state["extraction"].reminder

    if r is None or not r.due_date:
        return {"audit_log": [{"node": "reminder", "skipped": "no reminder or due date"}]}

    try:
        event = build_reminder_event(email, r)
    except ValueError as e:
        return {
            "status": "error",
            "error": f"reminder has an invalid date/time: {e}",
            "audit_log": [{"node": "reminder", "error": str(e)}],
        }

    service = config["configurable"]["calendar_service"]

    try:
        created = service.events().insert(calendarId="primary", body=event).execute()
    except HttpError as e:
        if e.resp.status == 409:   # same event ID already exists, so it was created before
            return {"audit_log": [{"node": "reminder", "skipped": "already exists"}]}
        return {
            "status": "error",
            "error": f"reminder failed: {e}",
            "audit_log": [{"node": "reminder", "error": str(e)}],
        }

    return {
        "executed_actions": ["create_reminder"],
        "status": "executed",
        "audit_log": [{"node": "reminder", "event_id": created["id"],
                       "due": f"{r.due_date} {r.due_time or '(all day)'}"}],
    }