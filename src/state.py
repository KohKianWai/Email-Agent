from pydantic import BaseModel, Field
from typing import Annotated, Literal, TypedDict, Optional
from operator import add

class Email(BaseModel):
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    received_at: str
    message_id_header: str | None = None   
    references: str | None = None      
    reply_to: str | None = None  

class EmailClassification(BaseModel):
    category: Literal["urgent", "spam", "meeting", "general"] = Field(
        description="The category that best describes the email."
    )

class MeetingDetails(BaseModel):
    date: Optional[str] = Field(
        default=None,
        description="Meeting date in YYYY-MM-DD format, if identifiable."
    )
    time: Optional[str] = Field(
        default=None,
        description="Meeting time in HH:MM 24-hour format, if identifiable."
    )
    duration: Optional[str] = Field(
        default=None,
        description="Meeting duration, if mentioned."
    )
    location: Optional[str] = Field(
        default=None,
        description="Meeting location or online meeting platform."
    )
    attendees: list[str] = Field(
        default_factory=list,
        description="People explicitly mentioned as meeting attendees."
    )

class ReminderDetails(BaseModel):
    title: str = Field(
        description="Short title describing what the user needs to remember."
    )
    description: Optional[str] = Field(
        default=None,
        description="Additional details about the task or reminder."
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Reminder date in YYYY-MM-DD format."
    )
    due_time: Optional[str] = Field(
        default=None,
        description="Reminder time in HH:MM 24-hour format."
    )

class EmailExtraction(BaseModel):
    summary: str = Field(description="One-sentence summary of the email.")
    reminder: Optional[ReminderDetails] = Field(
        default=None,
        description="Reminder details if the email contains a task or deadline worth reminding the user about; otherwise null."
    )
    requires_reply: bool = Field(description="True if the sender expects a response.")
    meeting: Optional[MeetingDetails] = Field(
        default=None, description="Only fill for meeting requests; otherwise null."
    )

class Approval(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    edited_draft: str | None = None
    feedback: str | None = None

class EmailState(TypedDict):
    # Input
    email: Email

    # Produced by nodes
    classification: EmailClassification
    extraction: EmailExtraction
    draft_reply: str | None

    # Human-in-the-loop
    approval: Approval | None

    # Output
    executed_actions: Annotated[list[str], add]  
    audit_log: Annotated[list[dict], add]         # every node appends an entry
    error: str
    status: Literal["new", "classified", "awaiting_approval", "extracted", "drafted",
                    "executed", "rejected", "needs_review", "error"]