from langchain_groq import ChatGroq
from ..state import EmailState, EmailExtraction
from langchain.messages import HumanMessage, SystemMessage
import os
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
from ..prompt import EMAIL_EXTRACTION_SYSTEM_PROMPT

load_dotenv()

TZ = ZoneInfo("Asia/Kuala_Lumpur")

def extract(state: EmailState) -> EmailState:
    now = datetime.now(TZ).strftime("%A, %Y-%m-%d %H:%M")
    category = state["classification"].category

    llm = ChatGroq(
            model="openai/gpt-oss-120b",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0,
            max_tokens=1000
    )

    structured_llm = llm.with_structured_output(EmailExtraction)

    messages = [
        SystemMessage(content=EMAIL_EXTRACTION_SYSTEM_PROMPT.format(
            category=category, now=now, tz=TZ.key
        )),
        HumanMessage(content=f"""
            Sender: {state['email'].sender}
            Subject: {state['email'].subject}
            Received: {state['email'].received_at}
            Email body:
            {state['email'].body}
        """)
    ]

    result = structured_llm.invoke(messages)

    return {
        "extraction": result,
        "status": "extracted",
        "audit_log": [{
            "node": "extract",
            "summary": result.summary,
            "has_meeting": result.meeting is not None,
            "n_action_items": len(result.action_items),
        }],
    }