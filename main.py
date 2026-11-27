import time
from googleapiclient.errors import HttpError
from langgraph.types import Command
from src.graph import graph
from gmail_client import create_gmail_service, create_calendar_service, get_email
from src.poller import load_history_id, current_history_id, save_history_id, get_new_message_ids, my_address, should_skip
import traceback

POLL_SECONDS = 30

ACTION_LABELS = {
    "send_email": "Reply sent",
    "create_reminder": "Calendar reminder created",
}

gmail = create_gmail_service()
calendar = create_calendar_service()

def make_config(email, gmail, calendar) -> dict:
    """Create a configuration."""
    return {"configurable": {
        "thread_id": email.id,
        "gmail_service": gmail,
        "calendar_service": calendar,
    }}

def start_email(email, gmail, calendar):
    """Run an email until it finishes or pauses for approval."""
    config = make_config(email, gmail, calendar)
    snapshot = graph.get_state(config)
    if snapshot.values:
        if not snapshot.next:
            print(f"skip {email.id}: already processed")
            return None

        interrupts = [i for task in snapshot.tasks for i in task.interrupts]
        if interrupts:
            print(f"\n>> resuming pending approval: {email.subject!r}")
            return config, {"__interrupt__": interrupts}
        return None
    
    print(f"\n>> processing: {email.subject!r} from {email.sender}")
    result = graph.invoke({"email": email, "status": "new"}, config)
    return config, result

def resolve_approvals(config, result):
    """Prompt in the terminal until the graph finishes."""
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        print("\n" + "=" * 60)
        print(f"From:    {payload['from']}")
        print(f"Subject: {payload['subject']}")
        print(f"Summary: {payload['summary']}")
        print(f"\n--- DRAFT ---\n{payload['draft']}\n")

        choice = input("approve / edit / reject? ").strip().lower()
        if choice == "edit":
            print("Enter new draft, finish with a line containing only END:")
            lines = []
            while (line := input()) != "END":
                lines.append(line)
            resume = {"decision": "edit", "edited_draft": "\n".join(lines)}
        elif choice == "approve":
            resume = {"decision": "approve"}
        else:
            resume = {"decision": "reject"}   # anything unclear is a rejection

        result = graph.invoke(Command(resume=resume), config)

    print(describe_outcome(result))
    print("-" * 60)

def process_batch(emails, gmail, calendar):
    # Run every email until it finishes or pauses
    pending = []
    for email in emails:
        started = start_email(email, gmail, calendar)
        if started is None:
            continue
        config, result = started
        if "__interrupt__" in result:
            pending.append((config, result))
        else:
            print(describe_outcome(result))
            print("-" * 60)

    # Then ask for approvals one by one
    for config, result in pending:
        resolve_approvals(config, result)

def run_watch(gmail, calendar):
    """Poll Gmail and process new emails automatically."""
    me = my_address(gmail)

    history_id = load_history_id()
    if history_id is None:
        history_id = current_history_id(gmail)   # start from "now"
        save_history_id(history_id)

    print(f"Watching inbox for {me} every {POLL_SECONDS}s. Ctrl+C to stop.")

    while True:
        try:
            ids, latest = get_new_message_ids(gmail, history_id)

            emails = []
            for mid in ids:
                email = get_email(gmail, mid)
                if should_skip(email, me):
                    continue
                emails.append(email)

            if emails:
                process_batch(emails, gmail, calendar)

            # Save only after the batch (including approvals) is done,
            # so a crash retries these emails instead of dropping them.
            history_id = latest
            save_history_id(history_id)

        except HttpError as e:
            if e.resp.status == 404:   # historyId too old, so restart from now
                print("History expired, resetting to the current point.")
                history_id = current_history_id(gmail)
                save_history_id(history_id)
            else:
                print("Gmail error:", e)
        except Exception as e:
            print("Unexpected error:", e)   # keep the loop alive
            traceback.print_exc()

        time.sleep(POLL_SECONDS)

def describe_outcome(result: dict) -> str:
    """Turn the final graph state into a short, human-readable summary."""
    status = result.get("status")
    classification = result.get("classification")
    extraction = result.get("extraction")
    approval = result.get("approval")
    actions = result.get("executed_actions", [])

    lines = []

    if classification:
        lines.append(f"Category: {classification.category}")
    if extraction:
        lines.append(f"Summary:  {extraction.summary}")

    if status == "error":
        lines.append(f"Result:   Failed. {result.get('error', 'unknown error')}")
        lines.append("          Nothing was sent or created.")
    elif classification and classification.category == "spam":
        lines.append("Result:   Marked as spam. No action taken.")
    elif approval and approval.decision == "reject":
        lines.append("Result:   You rejected the draft. No reply was sent.")
        lines.extend(f"          - {ACTION_LABELS.get(a, "")}" for a in actions)
    elif actions:
        lines.append("Result:   Done.")
        lines.extend(f"          - {ACTION_LABELS.get(a, "")}" for a in actions)
    elif extraction and not extraction.requires_reply:
        lines.append("Result:   No action needed. No reply is expected "
                     "and no deadline was found.")
    else:
        lines.append(f"Result:   Stopped (status: {status}). No actions were taken.")

    return "\n".join(lines)

if __name__ == "__main__":
    gmail = create_gmail_service()
    calendar = create_calendar_service()
    try:
        run_watch(gmail, calendar)
    except KeyboardInterrupt:
        print("\nStopped.")