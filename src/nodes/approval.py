from langgraph.types import interrupt, Command
from state import EmailState, Approval
from nodes.routing import needs_reminder
from langgraph.graph import END

def human_approval(state: EmailState) -> Command:
    decision = interrupt({
        "sender": state["email"].sender,
        "subject": state["email"].subject,
        "summary": state["extraction"].summary,
        "draft": state["draft_reply"],
        "options": ["approve", "edit", "reject"]
    })

    decision = Approval(**decision)

    update = {
        "approval": decision,
        "status": "rejected" if decision.decision == "reject" else "awaiting_approval",
        "audit_log": [{"node": "approval", "decision": decision.decision}],
    }

    if decision.decision == "reject":
        next_node = "reminder" if needs_reminder(state) else END
        return Command(goto=next_node, update=update)

    if decision.decision == "edit":
        if not decision.edited_draft or not decision.edited_draft.strip():
            raise ValueError("Edited draft cannot be empty.")
        
        update["draft_reply"] = decision.edited_draft

    return Command(goto="send_email", update=update)