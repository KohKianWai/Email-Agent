from ..state import EmailState
from langchain_core.runnables import RunnableConfig
from ..email_builder import build_reply

def send_email(state: EmailState, config: RunnableConfig):
    approval = state.get("approval")

    if approval is None or approval.decision not in ("approve", "edit"):
        return {
            "status": "error",
            "error": "send blocked: no approval on record",
            "audit_log": [{"node": "send_email", "blocked": True}],
        }

    body = (state.get("draft_reply") or "").strip()

    if not body:
        return {
            "status": "error",
            "error": "send blocked: empty draft",
            "audit_log": [{"node": "send_email", "blocked": "empty draft"}],
        }

    service = config["configurable"]["gmail_service"]
    email = state["email"]

    try:
        payload = build_reply(email, body)
        sent = service.users().messages().send(userId="me", body=payload).execute()
    except Exception as e:
        return {
            "status": "error",
            "error": f"send failed: {e}",
            "audit_log": [{"node": "send_email", "error": str(e)}],
        }

    return {
        "executed_actions": ["send_email"],
        "status": "executed",
        "audit_log": [{"node": "send_email", "sent_message_id": sent["id"]}],
    }