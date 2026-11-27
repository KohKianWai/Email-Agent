from ..state import EmailState, ReminderDetails
from langgraph.graph import END

def route_after_classify(state: EmailState) -> str:
    if state.get("status") == "error":
        return END
    category = state["classification"].category
    if category == "spam":
        return END
    else:
        return "extract"

def reminder_from_state(state: EmailState) -> ReminderDetails | None:
    extraction = state["extraction"]
    email = state["email"]

    if extraction.reminder and extraction.reminder.due_date:
        return extraction.reminder

    m = extraction.meeting
    if m and m.date:
        details = [f"Location: {m.location}" if m.location else None,
                   f"Duration: {m.duration}" if m.duration else None,
                   f"Attendees: {', '.join(m.attendees)}" if m.attendees else None]
        return ReminderDetails(
            title=f"Meeting: {email.subject}",
            description="\n".join(d for d in details if d) or None,
            due_date=m.date,
            due_time=m.time,
        )
    return None

def needs_reminder(state: EmailState) -> bool:
    return reminder_from_state(state) is not None

def route_after_extract(state: EmailState) -> str:
    if state.get("status") == "error":
        return END
    
    extraction = state["extraction"]

    if extraction.requires_reply:
        return "draft"
    if needs_reminder(state):
        return "reminder"
    else:
        return END

def route_after_draft(state: EmailState) -> str:
    return END if state.get("status") == "error" else "human_approval"

def route_after_send(state: EmailState) -> str:
    if state.get("status") == "error":
        return END
    return "reminder" if needs_reminder(state) else END


    