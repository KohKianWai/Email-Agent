from langgraph.graph import StateGraph, START, END
from state import EmailState
from nodes.classifier import classify
from nodes.extraction import extract
from nodes.draft import draft
from nodes.approval import human_approval
from nodes.send_email import send_email
from nodes.reminder import create_reminder
from nodes.routing import route_after_classify, route_after_draft, route_after_extract, route_after_send
from langgraph.checkpoint.memory import InMemorySaver

def build_graph(checkpointer):
    g = StateGraph(EmailState)

    g.add_node("classify", classify)
    g.add_node("extract", extract)
    g.add_node("draft", draft)
    g.add_node("human_approval", human_approval,
               destinations=("send_email", END))
    g.add_node("send_email", send_email)
    g.add_node("reminder", create_reminder)

    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route_after_classify,
                            {"extract": "extract", END: END})
    g.add_conditional_edges("extract", route_after_extract,
                            {"draft": "draft", "reminder": "reminder", END: END})
    g.add_conditional_edges("draft", route_after_draft,
                            {"human_approval": "human_approval", END: END})
    g.add_conditional_edges("send_email", route_after_send,
                            {"reminder": "reminder", END: END})
    g.add_edge("reminder", END)

    return g.compile(checkpointer=checkpointer)

graph = build_graph(InMemorySaver())
# png_data = graph.get_graph().draw_mermaid_png()

# with open("email_agent_graph.png", "wb") as f:
#     f.write(png_data)