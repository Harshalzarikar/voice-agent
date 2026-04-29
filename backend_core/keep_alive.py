import threading
import requests
import time
import os

def ping_self():
    # If RENDER_URL is not set, it will try localhost to at least keep the process active,
    # but the environment variable RENDER_URL should be set in the Render dashboard.
    url = os.environ.get("RENDER_URL", "http://127.0.0.1:8000/ping/")
    
    # We delay the first ping slightly to ensure the server is fully started
    time.sleep(30)
    
    while True:
        try:
            # Send the GET request to the ping endpoint
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"[Keep-Alive] Ping successful to {url}")
            else:
                print(f"[Keep-Alive] Ping received status {response.status_code}")
        except Exception as e:
            print(f"[Keep-Alive] Ping failed: {e}")
            
        # Ping every 10 minutes (600 seconds)
        # Render free tier sleeps after 15 minutes of inactivity
        time.sleep(600)

def start_keep_alive():
    # Start the daemon thread so it runs in the background and doesn't block shutdown
    thread = threading.Thread(target=ping_self, daemon=True)
    thread.start()
