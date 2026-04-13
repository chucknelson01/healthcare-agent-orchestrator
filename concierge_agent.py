import os
import httpx
import asyncio
import json
from typing import TypedDict
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

# LangGraph & LangChain imports
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

# A2A SDK & Utils
from a2a.client import ClientFactory, ClientConfig, create_text_message_object
from a2a.utils.message import get_message_text

# Local Helper Imports
from helpers import setup_env
from keycloak_utils import is_token_valid

setup_env()
app = FastAPI()

# --- 1. STATE & SCHEMAS ---

class MinimalState(TypedDict):
    query: str
    human_id: str
    nhi_token: str
    insurance_data: str
    doctor_data: str
    final_output: str

class SearchCriteria(BaseModel):
    city: str = Field(description="The city name")
    state: str = Field(description="The 2-letter state code")

# --- 2. NODES ---

async def a2a_policy_node(state: MinimalState):
    print("[*] Node: Querying A2A Policy Agent...")
    url = f"http://localhost:{os.getenv('POLICY_AGENT_PORT', '9999')}"
    async with httpx.AsyncClient(timeout=120.0) as httpx_client:
        try:
            client = await ClientFactory.connect(url, client_config=ClientConfig(httpx_client=httpx_client))
            msg = create_text_message_object(content=state['query'])
            text = ""
            async for response in client.send_message(msg):
                if hasattr(response, 'parts'):
                    text += get_message_text(response)
            return {"insurance_data": text}
        except Exception as e:
            return {"insurance_data": f"Policy Error: {str(e)}"}

async def mcp_provider_node(state: MinimalState):
    """MCP Node with Full Initialization Handshake"""
    print("[*] Node: Initializing MCP Session and calling tools...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(SearchCriteria)
    
    try:
        criteria = await structured_llm.ainvoke(state['query'])
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", "http://localhost:8000/sse") as response:
                lines = response.aiter_lines()
                post_url = None
                
                # 1. Handshake: Get Endpoint
                async for line in lines:
                    if line.startswith("data: "):
                        post_url = line.replace("data: ", "").strip()
                        break
                
                if not post_url: return {"doctor_data": "MCP Error: No endpoint."}
                full_url = f"http://localhost:8000{post_url}" if post_url.startswith("/") else post_url

                # 2. Handshake: Initialize Request
                # The server MUST see this before any tool calls
                init_payload = {
                    "jsonrpc": "2.0", "id": "init_1", "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "concierge-orchestrator", "version": "1.0.0"}
                    }
                }
                await client.post(full_url, json=init_payload)

                # 3. Handshake: Wait for Init Result from Stream
                async for line in lines:
                    if line.startswith("data: "):
                        if "result" in json.loads(line.replace("data: ", "")):
                            break # Initialization acknowledged

                # 4. Handshake: Send 'initialized' notification
                await client.post(full_url, json={
                    "jsonrpc": "2.0", "method": "notifications/initialized"
                })

                # 5. EXECUTE: The actual tool call
                tool_payload = {
                    "jsonrpc": "2.0", "id": "tool_1", "method": "tools/call",
                    "params": {
                        "name": "list_doctors",
                        "arguments": {"city": criteria.city, "state": criteria.state}
                    }
                }
                await client.post(full_url, json=tool_payload)

                # 6. CAPTURE: Wait for tool result
                async for line in lines:
                    if line.startswith("data: "):
                        mcp_msg = json.loads(line.replace("data: ", ""))
                        if "result" in mcp_msg and "content" in mcp_msg["result"]:
                            content = mcp_msg["result"].get("content", [{}])
                            return {"doctor_data": content[0].get("text", "No doctors found.")}
                
                return {"doctor_data": "MCP Error: Stream closed."}

    except Exception as e:
        print(f"[!] MCP Protocol Error: {str(e)}")
        return {"doctor_data": f"MCP Protocol Error: {str(e)}"}

async def final_summary_node(state: MinimalState):
    print("[*] Node: Final Synthesis...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = (
        f"Synthesize info for Human ID: {state['human_id']}\n"
        f"Insurance: {state['insurance_data']}\n"
        f"Doctors: {state['doctor_data']}"
    )
    res = await llm.ainvoke(prompt)
    return {"final_output": res.content}

# --- 3. GRAPH & API ---

builder = StateGraph(MinimalState)
builder.add_node("policy", a2a_policy_node)
builder.add_node("provider", mcp_provider_node)
builder.add_node("summary", final_summary_node)
builder.add_edge(START, "policy")
builder.add_edge(START, "provider")
builder.add_edge("policy", "summary")
builder.add_edge("provider", "summary")
builder.add_edge("summary", END)
graph = builder.compile()

@app.post("/query")
async def secure_orchestrator(request: dict, authorization: str = Header(None), x_human_sub: str = Header(None)):
    if not is_token_valid(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")
    initial_state = {
        "query": request.get("text", ""), "human_id": x_human_sub or "Unknown",
        "nhi_token": authorization, "insurance_data": "", "doctor_data": "", "final_output": ""
    }
    result = await graph.ainvoke(initial_state)
    return {"agent_response": result.get("final_output")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9996)
