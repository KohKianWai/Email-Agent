import base64
from email.message import EmailMessage
from .state import Email
from email.utils import parseaddr

def build_reply(email: Email, body: str) -> dict:
    _, to_addr = parseaddr(email.reply_to or email.sender)

    if not to_addr:
        raise ValueError("could not determine recipient address")

    subject = email.subject
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = EmailMessage()
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    # Threading headers so the reply stays in the same conversation
    if email.message_id_header:
        msg["In-Reply-To"] = email.message_id_header
        msg["References"] = (
            f"{email.references} {email.message_id_header}"
            if email.references else email.message_id_header
        )

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw, "threadId": email.thread_id}