from typing import Annotated, Sequence, TypedDict
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import re
import requests

from tools import clima_destino, recomendar_actividades


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next_tool: str
    human_approval: bool

llm = ChatOllama(model="llama3", temperature=0.3)

def verificar_ciudad_con_llm(nombre_ciudad: str) -> bool:
    """Verifica con LLM si el nombre corresponde a una ciudad real conocida."""
    pregunta = f"¿'{nombre_ciudad}' es una ciudad real del mundo? Responde solo con 'sí' o 'no'."
    respuesta = llm.invoke(pregunta)
    return "sí" in respuesta.content.lower()

def extraer_ciudad_automaticamente(mensaje: str) -> str:
    """
    Extrae una ciudad del mensaje usando limpieza avanzada y verificación con LLM.
    """
    
    try:
        mensaje_limpio = re.sub(
            r'(?i)\b(dime|dame|busca|muéstrame|enséñame|indícame|infórmame|cuál|cual|qué|que|el|la|los|las|en|de|sobre|por|favor|me|tiempo|clima|actividad|actividades|recomienda|lugares)\b',
            '',
            mensaje
        ).strip()

        if not mensaje_limpio:
            return None

        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": mensaje_limpio,
                "format": "json",
                "addressdetails": 1,
                "limit": 5,
                "accept-language": "es"
            },
            headers={"User-Agent": "TravelAssistant/1.0"},
            timeout=10
        )
        
        if response.status_code == 200 and response.json():
            resultados = response.json()
            
            for resultado in resultados:
                importancia = resultado.get("importance", 0)
                if importancia > 0.3:
                    ciudad = (
                        resultado.get("address", {}).get("city")
                        or resultado.get("address", {}).get("town")
                        or resultado.get("address", {}).get("state")
                        or resultado.get("name", "")
                    )
                    if ciudad:
                        print(f"✅ Ciudad encontrada: {ciudad} (importancia: {importancia})")

                        if verificar_ciudad_con_llm(ciudad):
                            print(f"🤖 LLM confirma que '{ciudad}' es una ciudad válida.")
                            return ciudad
                        else:
                            print(f"⚠️ LLM indica que '{ciudad}' puede no ser una ciudad.")

        return None

    except Exception as e:
        print(f"❌ Error en geocodificación: {e}")
        return None


def call_agent(state: AgentState):
    print("\n--- 🧠 Nodo: Invocando al modelo Ollama ---")

    messages = state["messages"]

    system_message = SystemMessage(
        content=(
            "Eres un asistente de viajes en español. "
            "Ayudas a los usuarios a planificar viajes, recomendar actividades, "
            "y dar información útil sobre destinos. "
            "Responde siempre en español, de manera natural y breve."
        )
    )

    full_context = [system_message] + list(messages)

    response = llm.invoke(full_context, )

    return {
        "messages": messages + [AIMessage(content=response.content)],
        "next_tool": "",
        "human_approval": False,
    }

def execute_tools(state: AgentState):
    print("\n--- 🧩 Nodo: Ejecutando herramientas externas ---")
    messages = state["messages"]
    human_messages = [m for m in messages if m.type == "human"]

    if not human_messages:
        return {**state, "messages": messages + [AIMessage(content="No hay mensaje humano para procesar.")]}

    last_human_message = human_messages[-1].content
    msg_lower = last_human_message.lower()

    palabras_clima = ["clima", "tiempo", "temperatura"]
    palabras_actividades = ["actividad", "actividades", "hacer", "recomienda", "lugares", "sitios", "visitar", "recomiendame"]

    ciudad = None
    interes = "cultura" 
    output_message = None

    if any(p in msg_lower for p in palabras_clima):
        ciudad = extraer_ciudad_automaticamente(last_human_message)
        print(f"🔍 Intento de extraer ciudad para clima: {ciudad}")
        if ciudad:
            output_message = clima_destino.invoke({"ciudad": ciudad})
            print(f"✅ Clima obtenido para {ciudad}")

    elif any(p in msg_lower for p in palabras_actividades):
        ciudad = extraer_ciudad_automaticamente(last_human_message)
        print(f"🔍 Intento de extraer ciudad para actividades: {ciudad}")
        if ciudad:
            for i in ["cultura", "aventura", "gastronomia", "historia", "naturaleza"]:
                if i in msg_lower:
                    interes = i
                    break
            print(f"📍 Ciudad: {ciudad}, Interés detectado: {interes}")
            output_message = recomendar_actividades.invoke({"ciudad": ciudad, "interes": interes})
            print(f"✅ Actividades obtenidas para {ciudad} ({interes})")

    if output_message:
        ai_messages = [i for i, msg in enumerate(messages) if msg.type == "ai"]
        if ai_messages:
            last_ai_index = ai_messages[-1]
            new_messages = messages.copy()
            new_messages[last_ai_index] = AIMessage(content=output_message)
            final_messages = new_messages
        else:
            final_messages = messages + [AIMessage(content=output_message)]
    else:
        print("⚠️ No se ejecutó ninguna tool. Se mantiene respuesta del LLM.")
        final_messages = messages

    return {
        **state,
        "messages": final_messages,
        "next_tool": "",
        "human_approval": False,
    }



def human_intervention(state: AgentState):
    print("\n--- 🧍‍♂️ Nodo: Requiere aprobación humana ---")
    mensaje = "Esperando aprobación humana..."
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=mensaje)],
        "next_tool": "",
        "human_approval": True, 
    }


def router(state: AgentState):
    messages = state["messages"]

    human_messages = [msg for msg in messages if msg.type == "human"]
    if not human_messages:
        return "end_conversation"
        
    last_human = human_messages[-1].content.lower()
    print(f"🔀 Router simple analizando: '{last_human}'")

    herramientas_keywords = [
        "clima", "tiempo", "actividad", "actividades", "recomienda", "lugares", "visitar"
    ]
    
    intervencion_keywords = [
        "reserva", "reservar", "pago", "pagar"
    ]

    for keyword in herramientas_keywords:
        if keyword in last_human:
            print(f"🛠️ Router: Detectado '{keyword}' -> herramientas")
            return "execute_tools"

    for keyword in intervencion_keywords:
        if keyword in last_human:
            print(f"🛑 Router: Detectado '{keyword}' -> intervención humana")
            return "human_intervention"
    
    print("💬 Router: No se detectó tool → volver a call_agent")
    return "call_agent"


workflow = StateGraph(AgentState)

workflow.add_node("call_agent", call_agent)
workflow.add_node("execute_tools", execute_tools)
workflow.add_node("human_intervention", human_intervention)
workflow.add_node("end_conversation", lambda state: state)  

workflow.set_entry_point("call_agent")

workflow.add_conditional_edges(
    "call_agent",
    router,
    {
        "execute_tools": "execute_tools",
        "human_intervention": "human_intervention",
        "call_agent": "end_conversation",
        "end_conversation": "end_conversation"  
    }
)


workflow.add_edge("execute_tools", "end_conversation")
workflow.add_edge("human_intervention", "end_conversation")
workflow.add_edge("end_conversation", END)

app = workflow.compile()