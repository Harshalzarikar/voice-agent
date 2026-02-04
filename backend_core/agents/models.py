from django.db import models

class Agent(models.Model):
    name = models.CharField(max_length=100)
    system_prompt = models.TextField()
    voice_id = models.CharField(max_length=100, default='aura-asteria-en') # default deepgram voice
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='agents', null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class ChatSession(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=200, blank=True, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} - {self.agent.name}"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages', null=True)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20) # 'user' or 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} - {self.agent.name}"
