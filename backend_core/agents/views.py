import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (one level above backend_core)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

from rest_framework import viewsets, permissions
from .models import Agent, ChatMessage, ChatSession
from .serializers import AgentSerializer, ChatMessageSerializer, ChatSessionSerializer

class AgentViewSet(viewsets.ModelViewSet):
    serializer_class = AgentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Agent.objects.all()

    def perform_create(self, serializer):
        serializer.save()

class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = ChatSession.objects.all()
        agent_id = self.request.query_params.get('agent')
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save()

class ChatMessageViewSet(viewsets.ModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = ChatMessage.objects.all()
        session_id = self.request.query_params.get('session')
        if session_id:
            queryset = queryset.filter(session_id=session_id)
        return queryset

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from livekit import api
import os
import uuid

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_livekit_token(request):
    room_name = request.GET.get('room', 'test-room')
    participant_name = request.GET.get('username', f'user-{uuid.uuid4().hex[:8]}')
    
    api_key = os.environ.get("LIVEKIT_API_KEY")
    api_secret = os.environ.get("LIVEKIT_API_SECRET")
    
    if not api_key or not api_secret:
        return Response({"error": "LiveKit credentials not configured. Please check .env"}, status=500)

    token = api.AccessToken(api_key, api_secret) \
        .with_identity(participant_name) \
        .with_name(participant_name) \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
        ))
    
    return Response({
        "token": token.to_jwt(),
        "url": os.environ.get("LIVEKIT_URL")
    })
