# VoiceAI Agent - Project Summary

## 1. Project Overview
This project is a **Real-Time AI Voice Agent**. It allows a user to speak into their microphone and have a seamless, spoken conversation with an AI. The system is designed to be extremely fast (ultra-low latency) and very lightweight, so it can run entirely on a free server with only 512MB of RAM.

---

## 2. What We Used (The Tech Stack)

**Frontend (User Interface):**
*   **React.js:** Used to build the website.
*   **Web Audio API:** Used to securely capture raw microphone audio directly from the browser.

**Backend (The Server):**
*   **Django:** Used for the main database, saving user accounts, login systems, and chat history.
*   **FastAPI & WebSockets:** Used specifically for the audio streaming. WebSockets allow continuous, real-time audio to flow back and forth without refreshing the page.

**Database & Hosting:**
*   **Supabase (PostgreSQL):** A cloud database used to permanently store user accounts and chats.
*   **Docker & Render:** The entire app is packaged into a Docker container and hosted on Render's free tier.

---

## 3. The AI Models (Where they are hosted)

To keep the server memory usage at almost 0MB, we offloaded all heavy AI processing to external Cloud APIs instead of running them locally:

*   **Speech-to-Text (Hearing):** We used **Whisper Large v3 Turbo**, hosted on the **Groq API**. It instantly converts the user's voice into text.
*   **LLM / Brain (Thinking):** We used **Llama 3.3 70B**, also hosted on the **Groq API**. LangGraph is used to route the conversation and remember chat history.
*   **Text-to-Speech (Speaking):** We used **Kokoro-TTS**, hosted on a free **HuggingFace Space API**. It turns the AI's text response back into lifelike human audio.

---

## 4. How the "Voice Activity Detection" (VAD) Works
*   **We used a Custom RMS algorithm.** Instead of using heavy machine learning tools to detect when someone is speaking, we wrote a simple mathematical script in Python. It constantly measures the volume (Root Mean Square) of the microphone. If the volume goes up, it knows the user is speaking. If it goes quiet for 0.6 seconds, it knows the user has stopped, and it sends the audio to the AI.

---

## 5. What We DID NOT Use (And Why)

*   **We DID NOT use Local AI Models:** We originally tried to run OpenAI Whisper locally on the server. However, it consumed over 500MB of RAM and crashed the server. Switching to the Groq API fixed this completely.
*   **We DID NOT use WebRTC or Silero VAD:** These are standard libraries for voice detection, but they are very heavy. Our custom RMS mathematical VAD does the exact same job using almost zero memory.
*   **We DID NOT use SQLite:** SQLite deletes data every time the free server restarts. We switched to Supabase to keep user data safe and permanent.
*   **We DID NOT use paid APIs:** Every service we used (Groq, HuggingFace, Supabase, Render) is operating on a free tier, making the running cost of this project **$0.00**.
