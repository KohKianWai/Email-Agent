from langchain_groq import ChatGroq
from ..state import EmailState
from langchain.messages import HumanMessage, SystemMessage
from ..prompt import DRAFT_REPLY_SYSTEM_PROMPT
import os
from dotenv import load_dotenv

load_dotenv()

USER_NAME = os.getenv("USER_NAME", "Your Name")

EMAIL_TONE_INSTRUCTIONS = {
    "urgent": (
        "Respond promptly and professionally. Recognize the sender's concern, "
        "acknowledge receipt of their message, and reassure them that you are "
        "currently looking into the matter. Avoid committing to a specific "
        "resolution time unless explicitly requested."
    ),
    "meeting": (
        "Maintain a polite and professional tone when responding to meeting "
        "requests. Acknowledge the suggested schedule and tentatively confirm "
        "your availability. Include the proposed location or meeting platform "
        "when provided. If no schedule is mentioned, politely ask the sender "
        "to suggest a suitable time. Do not make up meeting details."
    ),
    "general": (
        "Use a friendly, polite, and professional tone. Keep the response "
        "concise and address the sender's questions based solely on the "
        "information provided in the email. If additional information is "
        "needed, acknowledge the request and indicate that you will follow up."
    ),
}

def format_meeting(state: EmailState) -> str:
    m = state["extraction"].meeting
    if not m:
        return "none"
    parts = {
        "date": m.date, "time": m.time, "duration": m.duration,
        "location": m.location, "attendees": m.attendees or None,
    }
    return ", ".join(f"{k}: {v}" for k, v in parts.items() if v) or "none"

def draft(state: EmailState) -> EmailState:

    email = state["email"]
    category = state["classification"].category
    extraction = state["extraction"]

    llm = ChatGroq(
            model="openai/gpt-oss-120b",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
            max_tokens=1000
    )

    messages = [
        SystemMessage(content=DRAFT_REPLY_SYSTEM_PROMPT.format(
            user_name=USER_NAME,
            category=category,
            guidance=EMAIL_TONE_INSTRUCTIONS.get(category, EMAIL_TONE_INSTRUCTIONS["general"]),
            summary=extraction.summary,
            meeting=format_meeting(state)
        )),
        HumanMessage(content=f"""
        Original Email:

        Sender: {email.sender}
        Subject: {email.subject}
        Received: {email.received_at}

        Email Body:
        {email.body}
        """)
    ]

    response = llm.invoke(messages)

    draft = response.content.strip()

    return {
        "draft_reply": draft,
        "status": "drafted",
        "audit_log": [{
            "node": "draft", 
            "chars": len(draft)
        }],
    }