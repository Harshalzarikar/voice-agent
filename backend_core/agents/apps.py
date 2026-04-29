from django.apps import AppConfig


class AgentsConfig(AppConfig):
    name = 'agents'

    def ready(self):
        # We wrap in a try-except just in case to prevent breaking the app startup
        try:
            import sys
            # Only start the keep-alive thread if running as a server (not during migrations)
            if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0] or 'uvicorn' in sys.argv[0]:
                from keep_alive import start_keep_alive
                start_keep_alive()
        except Exception as e:
            print(f"[Keep-Alive] Failed to start: {e}")
