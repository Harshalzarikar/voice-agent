import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.voice_processor import VoiceProcessor

router = APIRouter()

@router.websocket("/chat/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    
    # Fetch Agent Configuration from Django
    system_prompt = "You are a helpful assistant."
    voice_id = "aura-asteria-en"
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:8000/api/agents/{agent_id}/")
            if resp.status_code == 200:
                data = resp.json()
                system_prompt = data.get("system_prompt", system_prompt)
                voice_id = data.get("voice_id", voice_id)
                print(f"Loaded Agent {agent_id}: {data.get('name')}")
            else:
                print(f"Failed to fetch agent {agent_id}, using defaults. Status: {resp.status_code}")
    except Exception as e:
        print(f"Error fetching agent {agent_id}: {e}")

    processor = VoiceProcessor(agent_id, websocket, system_prompt, voice_id)
    is_ready = await processor.start()
    
    if not is_ready:
        await websocket.close(code=1011)
        return

    print(f"Connection accepted for agent {agent_id}")
    try:
        while True:
            # Expecting binary audio data
            data = await websocket.receive_bytes()
            # Process
            await processor.process_audio(data)
    except WebSocketDisconnect:
        print(f"Client disconnected for agent {agent_id}")
        await processor.stop()
    except Exception as e:
        print(f"Error: {e}")
        await processor.stop()
