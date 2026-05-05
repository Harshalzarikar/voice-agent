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
