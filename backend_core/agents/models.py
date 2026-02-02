from django.db import models

class Agent(models.Model):
    name = models.CharField(max_length=100)
    system_prompt = models.TextField()
    voice_id = models.CharField(max_length=100, default='aura-asteria-en') # default deepgram voice
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
