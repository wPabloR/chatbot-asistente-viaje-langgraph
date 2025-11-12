import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage

# Importamos el grafo compilado y el estado
from agent import app, AgentState


app_fastapi = FastAPI(title="Asistente de Viaje LangGraph API (Ollama)")

app_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_storage: Dict[str, Dict[str, Any]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class MessageResponse(BaseModel):
    session_id: str
    response: str
    requires_approval: bool
    full_history: List[Dict[str, Any]]

class ApprovalRequest(BaseModel):
    session_id: str
    approved: bool


@app_fastapi.get("/")
async def root():
    return {"message": "Asistente de Viaje con LangGraph + Ollama está en funcionamiento."}


def extract_messages(event: dict) -> Optional[List[Any]]:
    if event and "messages" in event:
        return event["messages"]
    if event and "call_agent" in event and "messages" in event["call_agent"]:
        return event["call_agent"]["messages"]
    if event and "execute_tools" in event and "messages" in event["execute_tools"]:
        return event["execute_tools"]["messages"]
    if event and "human_intervention" in event and "messages" in event["human_intervention"]:
        return event["human_intervention"]["messages"]
    return None


@app_fastapi.post("/chat", response_model=MessageResponse)
async def chat_handler(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    user_message = HumanMessage(content=request.message)
 
    if session_id not in session_storage:
        print(f"--- 🆕 Nueva sesión: {session_id} ---")
        state: AgentState = {
            "messages": [user_message],
            "next_tool": "",
            "human_approval": False,
        }
        config = {"configurable": {"thread_id": session_id}}
        session_storage[session_id] = {"app": app, "config": config, "state": state}
    else:
        print(f"--- 🔄 Sesión existente: {session_id} ---")
        state = {
            "messages": session_storage[session_id]["state"]["messages"] + [user_message],
            "next_tool": "",
            "human_approval": False,
        }

    session = session_storage[session_id]
    final_output = None

    async for event in session["app"].astream(state, session["config"]):
        messages = extract_messages(event)
        if messages:
            final_output = {
                **state,
                "messages": messages,
                "human_approval": event.get("human_approval", False)
            }
        else:
            print("Evento parcial:", event)

    if not final_output or "messages" not in final_output:
        raise HTTPException(status_code=500, detail="El flujo del agente no devolvió un estado válido.")

    session_storage[session_id]["state"] = final_output
    last_state: AgentState = final_output
    last_message = last_state["messages"][-1]

    requires_approval = (
        "esperando aprobación humana" in last_message.content.lower() or 
        last_state.get("human_approval", False)
    )

    full_history = []
    for msg in last_state["messages"]:
        content = getattr(msg, "content", str(msg))
        msg_type = getattr(msg, "type", "ai")
        full_history.append({"type": msg_type, "content": content})

    return MessageResponse(
        session_id=session_id,
        response=last_message.content,
        requires_approval=requires_approval,
        full_history=full_history
    )

@app_fastapi.post("/approve", response_model=MessageResponse)
async def approve_handler(request: ApprovalRequest):
    session = session_storage.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada.")

    current_state = session["state"]
    current_state["human_approval"] = request.approved

    final_output = None
    async for output in session["app"].astream(current_state, session["config"]):
        messages = extract_messages(output)
        if messages:
            final_output = {
                **current_state,
                "messages": messages,
                "human_approval": output.get("human_approval", False)
            }
        else:
            print("Evento parcial tras aprobación:", output)

    if not final_output:
        raise HTTPException(status_code=500, detail="No se obtuvo una respuesta del grafo tras la aprobación.")

    session_storage[request.session_id]["state"] = final_output

    feedback = (
        "APROBADO. El plan fue confirmado y la reserva completada."
        if request.approved else
        "PROPUESTA RECHAZADA. Por favor, ajusta tu solicitud."
    )

    full_history = []
    for msg in final_output["messages"]:
        content = getattr(msg, "content", str(msg))
        msg_type = getattr(msg, "type", "ai")
        full_history.append({"type": msg_type, "content": content})

    return MessageResponse(
        session_id=request.session_id,
        response=feedback,
        requires_approval=False,
        full_history=full_history
    )
