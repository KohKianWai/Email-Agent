from langchain_groq import ChatGroq
from ..state import EmailState, EmailClassification
from langchain.messages import HumanMessage, SystemMessage
from ..prompt import EMAIL_CLASSIFY_SYSTEM_PROMPT
import os
from dotenv import load_dotenv

load_dotenv()

def classify(state: EmailState) -> EmailState:
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_tokens=1000
    )

    structured_llm = llm.with_structured_output(EmailClassification, method="json_schema")

    messages = [
        SystemMessage(content=EMAIL_CLASSIFY_SYSTEM_PROMPT),
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
        "classification": result,
        "status": "classified",
        "audit_log": [{
            "node": "classify",
            "category": result.category,
        }],
    }