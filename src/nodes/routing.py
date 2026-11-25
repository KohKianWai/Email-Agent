from state import EmailState
from langgraph.graph import END

def route_after_classify(state: EmailState) -> str:
    if state.get("status") == "error":
        return END
    category = state["classification"].category
    if category == "spam":
        return END
    else:
        return "extract"

def needs_reminder(state: EmailState) -> bool:
    extraction = state["extraction"]
    return extraction.meeting is not None or extraction.reminder is not None

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


    