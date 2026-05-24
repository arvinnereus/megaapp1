# OpenAI Realtime Voice + Dashboard Orb Setup Guide

Complete guide to hooking up the OpenAI Realtime API for live voice conversations with a visual orb/bubble UI in a Flask dashboard. This is how Jarvis/Jackie's voice mode works — click the orb, talk, get instant spoken responses through WebSocket.

---

## Architecture Overview

```
Browser (Dashboard)                    Your Flask Server               OpenAI
┌──────────────────┐                  ┌──────────────┐              ┌─────────────┐
│  Orb UI (click)  │                  │              │              │             │
│       ↓          │  POST /session   │  Creates     │   POST       │  Returns    │
│  startRealtime() │ ───────────────→ │  ephemeral   │ ────────────→│  client     │
│       ↓          │                  │  token       │              │  secret     │
│  WebSocket ──────│──────────────────│──────────────│──────────────│→ Realtime   │
│  (direct to      │  wss://api.openai.com/v1/realtime              │  API        │
│   OpenAI)        │                  │              │              │             │
│  Mic → PCM audio │ ═══════════════════════════════════════════════│→ Whisper    │
│  Speaker ← audio │ ←══════════════════════════════════════════════│← TTS        │
└──────────────────┘                  └──────────────┘              └─────────────┘
```

**Key insight:** The browser connects directly to OpenAI via WebSocket. Your server only creates the ephemeral token — it never touches the audio stream. This keeps latency ultra-low.

---

## Step 1: Get an OpenAI API Key

1. Go to [platform.openai.com](https://platform.openai.com/)
2. Create an API key with **Realtime** access
3. Add to your `.env`:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### Cost

- **Realtime API:** ~$0.06/min for audio input + output (gpt-4o-mini-realtime-preview)
- **Idle timeout recommended:** Auto-disconnect after 2-5 min of silence to avoid burning credits

---

## Step 2: Server-Side — Ephemeral Token Endpoint

The browser can't hold your OpenAI key. Instead, your server creates a short-lived token:

```python
# app.py — Flask route

@app.post("/api/realtime/session")
def realtime_session():
    """Create an ephemeral OpenAI Realtime API token for browser WebSocket."""
    import requests
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY not set"}), 503

    try:
        r = requests.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini-realtime-preview",
                "voice": "shimmer",           # Options: alloy, echo, fable, onyx, nova, shimmer
                "instructions": "Your system prompt here — personality, rules, context.",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",      # Server-side voice activity detection
                    "threshold": 0.5,          # Sensitivity (0.0-1.0, lower = more sensitive)
                    "prefix_padding_ms": 300,  # Audio before speech start to include
                    "silence_duration_ms": 500, # Silence before considering turn complete
                },
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return jsonify({
            "client_secret": data["client_secret"]["value"],
            "expires_at": data.get("expires_at"),
        })
    except Exception as e:
        return jsonify({"error": "Voice service unavailable"}), 500
```

### Voice Options

| Voice | Style |
|-------|-------|
| `alloy` | Neutral, balanced |
| `echo` | Warm, conversational |
| `fable` | Expressive, storytelling |
| `onyx` | Deep, authoritative |
| `nova` | Friendly, upbeat |
| `shimmer` | Clear, professional |

### System Instructions

The `instructions` field is your personality prompt. Keep it concise — it's sent with every session. Example:

```python
"instructions": """You are a personal AI assistant.
Keep responses to 1-3 sentences — you're in a voice conversation, not writing an essay.
Talk naturally with contractions and casual language.
Help with productivity, tasks, planning, and quick questions."""
```

---

## Step 3: Client-Side — WebSocket Connection

### HTML — The Orb

```html
<div class="orb-area">
  <div class="orb-wrap" id="voice-orb" onclick="toggleVoice()">
    <div class="orb-ring"></div>
    <div class="orb-ring"></div>
    <div class="orb-ring"></div>
    <div class="orb"></div>
  </div>
</div>
<div class="orb-status" id="orb-status">click orb to activate voice</div>
```

### CSS — Animated Orb

```css
.orb-area {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.orb-wrap {
  position: relative;
  width: 120px;
  height: 120px;
  cursor: pointer;
}

.orb {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 60px; height: 60px;
  border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #c8a960, #8b6914);
  box-shadow: 0 0 30px rgba(200, 169, 96, 0.3);
  transition: all 0.3s ease;
}

.orb-ring {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  border: 1px solid rgba(200, 169, 96, 0.2);
  opacity: 0;
  transition: all 0.3s;
}
.orb-ring:nth-child(1) { width: 80px; height: 80px; }
.orb-ring:nth-child(2) { width: 100px; height: 100px; }
.orb-ring:nth-child(3) { width: 120px; height: 120px; }

/* Active/listening state */
.orb-wrap.listening .orb {
  box-shadow: 0 0 60px rgba(200, 169, 96, 0.6);
}
.orb-wrap.listening .orb-ring {
  opacity: 1;
  animation: orbPulse 2s ease-in-out infinite;
}
.orb-ring:nth-child(2) { animation-delay: 0.3s; }
.orb-ring:nth-child(3) { animation-delay: 0.6s; }

@keyframes orbPulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.3; }
  50% { transform: translate(-50%, -50%) scale(1.1); opacity: 0.6; }
}

.orb-status {
  text-align: center;
  font-size: 0.8em;
  color: #888;
  margin-top: 8px;
}
.orb-status.active { color: #c8a960; }
```

### JavaScript — Full Realtime Voice Implementation

```javascript
let realtimeWs = null;
let realtimeActive = false;
let realtimeWantActive = false;
let realtimeMic = null;
let realtimeProcessor = null;
let realtimeIdleTimer = null;
let realtimeLastActivity = 0;
const REALTIME_IDLE_MS = 120000; // 2 min idle → auto-disconnect

// ── Toggle Voice ──────────────────────────────────────────────
function toggleVoice() {
  if (realtimeActive) {
    stopRealtime();
  } else {
    startRealtime();
  }
}

// ── Start Realtime Session ────────────────────────────────────
async function startRealtime(isReconnect = false) {
  if (realtimeActive && !isReconnect) { stopRealtime(); return; }

  realtimeWantActive = true;
  realtimeLastActivity = Date.now();
  startIdleTimer();

  try {
    // 1. Get ephemeral token from your server
    const res = await fetch('/api/realtime/session', { method: 'POST' });
    if (!res.ok) {
      const err = await res.json();
      console.error('Session error:', err);
      return;
    }
    const { client_secret } = await res.json();

    // 2. Connect WebSocket directly to OpenAI
    const wsUrl = 'wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview';
    realtimeWs = new WebSocket(wsUrl, [
      'realtime',
      `openai-insecure-api-key.${client_secret}`,
      'openai-beta.realtime-v1',
    ]);

    realtimeWs.onopen = async () => {
      realtimeActive = true;
      updateOrbUI(true);

      // Start capturing microphone
      await startMicCapture();
    };

    realtimeWs.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      handleRealtimeMessage(msg);
    };

    realtimeWs.onerror = () => {
      cleanup();
      if (realtimeWantActive) setTimeout(() => startRealtime(true), 1000);
    };

    realtimeWs.onclose = () => {
      cleanup();
      if (realtimeWantActive) setTimeout(() => startRealtime(true), 500);
    };

  } catch (e) {
    console.error('Failed to start realtime:', e);
    if (realtimeWantActive) setTimeout(() => startRealtime(true), 2000);
  }
}

// ── Stop Realtime ─────────────────────────────────────────────
function stopRealtime() {
  realtimeWantActive = false;
  if (realtimeIdleTimer) { clearInterval(realtimeIdleTimer); realtimeIdleTimer = null; }
  cleanup();
}

function cleanup() {
  if (realtimeProcessor) { realtimeProcessor.disconnect(); realtimeProcessor = null; }
  if (realtimeMic) { realtimeMic.getTracks().forEach(t => t.stop()); realtimeMic = null; }
  if (realtimeWs?.readyState === WebSocket.OPEN) realtimeWs.close();
  realtimeWs = null;
  realtimeActive = false;
  updateOrbUI(false);
}

// ── Microphone Capture ────────────────────────────────────────
async function startMicCapture() {
  try {
    realtimeMic = await navigator.mediaDevices.getUserMedia({ audio: true });
    const audioCtx = new AudioContext({ sampleRate: 24000 });
    const source = audioCtx.createMediaStreamSource(realtimeMic);

    // Process mic audio into PCM16 chunks for OpenAI
    realtimeProcessor = audioCtx.createScriptProcessor(4096, 1, 1);
    realtimeProcessor.onaudioprocess = (e) => {
      if (!realtimeWs || realtimeWs.readyState !== WebSocket.OPEN) return;

      const float32 = e.inputBuffer.getChannelData(0);
      // Convert Float32 → Int16 PCM
      const int16 = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        int16[i] = Math.max(-32768, Math.min(32767, Math.floor(float32[i] * 32768)));
      }

      // Send as base64 to OpenAI
      const base64 = btoa(String.fromCharCode(...new Uint8Array(int16.buffer)));
      realtimeWs.send(JSON.stringify({
        type: 'input_audio_buffer.append',
        audio: base64,
      }));
    };

    source.connect(realtimeProcessor);
    realtimeProcessor.connect(audioCtx.destination);
  } catch (e) {
    console.error('Mic capture failed:', e);
  }
}

// ── Handle OpenAI Messages ────────────────────────────────────
let audioQueue = [];
let audioPlaying = false;

function handleRealtimeMessage(msg) {
  realtimeLastActivity = Date.now();

  switch (msg.type) {
    case 'response.audio.delta':
      // Queue audio chunk for playback
      audioQueue.push(msg.delta);
      if (!audioPlaying) playNextAudioChunk();
      break;

    case 'response.audio_transcript.delta':
      // AI is speaking — show transcript in chat bubble
      appendOrUpdateBubble('assistant', msg.delta);
      break;

    case 'conversation.item.input_audio_transcription.completed':
      // User's speech transcribed
      appendBubble('user', msg.transcript);
      break;

    case 'response.done':
      // Response complete
      break;

    case 'error':
      console.error('Realtime error:', msg.error);
      break;
  }
}

// ── Audio Playback ────────────────────────────────────────────
async function playNextAudioChunk() {
  if (audioQueue.length === 0) { audioPlaying = false; return; }
  audioPlaying = true;

  const base64 = audioQueue.shift();
  const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));

  // PCM16 mono 24kHz → play via AudioContext
  const audioCtx = new AudioContext({ sampleRate: 24000 });
  const float32 = new Float32Array(bytes.length / 2);
  const view = new DataView(bytes.buffer);
  for (let i = 0; i < float32.length; i++) {
    float32[i] = view.getInt16(i * 2, true) / 32768;
  }

  const buffer = audioCtx.createBuffer(1, float32.length, 24000);
  buffer.getChannelData(0).set(float32);
  const source = audioCtx.createBufferSource();
  source.buffer = buffer;
  source.connect(audioCtx.destination);
  source.onended = () => playNextAudioChunk();
  source.start();
}

// ── Idle Timer ────────────────────────────────────────────────
function startIdleTimer() {
  if (realtimeIdleTimer) clearInterval(realtimeIdleTimer);
  realtimeIdleTimer = setInterval(() => {
    if (realtimeActive && Date.now() - realtimeLastActivity > REALTIME_IDLE_MS) {
      console.log('Idle timeout — disconnecting');
      stopRealtime();
    }
  }, 10000);
}

// ── UI Update ─────────────────────────────────────────────────
function updateOrbUI(active) {
  const orb = document.getElementById('voice-orb');
  const status = document.getElementById('orb-status');
  if (active) {
    orb.classList.add('listening');
    status.textContent = 'listening...';
    status.classList.add('active');
  } else {
    orb.classList.remove('listening');
    status.textContent = 'click orb to activate voice';
    status.classList.remove('active');
  }
}
```

---

## Step 4: Environment Variables

```env
# Required
OPENAI_API_KEY=sk-your-key-here

# Optional: Fish.audio TTS fallback (for text chat responses)
FISH_AUDIO_API_KEY=your-fish-key
FISH_AUDIO_VOICE_ID=your-voice-id
```

---

## How It All Fits Together

1. **User clicks the orb** → `toggleVoice()` fires
2. **Browser requests ephemeral token** → `POST /api/realtime/session` to your Flask server
3. **Server calls OpenAI** → Gets a short-lived `client_secret` (no long-lived key exposed to browser)
4. **Browser opens WebSocket** → Direct to `wss://api.openai.com/v1/realtime` with the ephemeral token
5. **Mic capture starts** → Browser captures audio, converts to PCM16, sends via WebSocket
6. **OpenAI processes** → Whisper transcribes speech, GPT generates response, TTS speaks it back
7. **Audio streams back** → PCM16 chunks arrive via WebSocket, browser plays them instantly
8. **Transcripts appear** → Both user speech and AI speech show in chat bubbles
9. **Idle timeout** → After 2 min silence, auto-disconnects to save credits

---

## Best Practices

### Cost Control
- **Idle timeout is critical.** Without it, an open session burns ~$0.06/min even when silent
- Use `gpt-4o-mini-realtime-preview` (cheapest) unless you need full GPT-4o quality
- Auto-reconnect on demand, not permanently

### Audio Quality
- **24kHz sample rate** — OpenAI Realtime expects this, don't change it
- **PCM16 format** — raw 16-bit signed integers, mono channel
- **Chunk size 4096** — good balance of latency vs overhead

### UX Tips
- Show visual feedback (pulsing orb) immediately on click, before connection completes
- Display transcripts in real-time as both parties speak
- Add pause/mute buttons so users can control without disconnecting
- Auto-reconnect on network blips (WebSocket close/error handlers)

### Security
- **Never expose your OpenAI API key to the browser** — always use ephemeral tokens
- Ephemeral tokens expire quickly (~60 seconds) and are single-use
- Your server is the only place that holds the real API key

---

## Troubleshooting

### "Voice service unavailable"
- Check `OPENAI_API_KEY` is set in `.env`
- Verify the key has Realtime API access (not all keys do)
- Check OpenAI status page for outages

### No audio from microphone
- Browser needs HTTPS (or localhost) for `getUserMedia()`
- User must grant microphone permission
- Check `navigator.mediaDevices` is available

### Audio plays but sounds garbled
- Ensure sample rate is 24000 Hz on both capture and playback
- PCM16 conversion must match: Float32 → Int16 (multiply by 32768)

### WebSocket disconnects immediately
- Ephemeral token may have expired — token creation and WebSocket open must happen quickly
- Check browser console for WebSocket close code and reason

### High latency
- The WebSocket goes browser → OpenAI directly (no server hop for audio)
- If slow, it's OpenAI's processing time, not your architecture
- `gpt-4o-mini-realtime-preview` is faster than full GPT-4o

---

## File Reference (Jarvis 2.0 Implementation)

| File | What It Does |
|------|-------------|
| `app.py:1016-1054` | `/api/realtime/session` — ephemeral token endpoint |
| `app.py:1057-1081` | Jackie personality instructions |
| `app.py:976-1012` | Fish.audio TTS fallback (for text chat) |
| `jarvis/tts_client.py` | Fish.audio TTS client (synthesize + stream) |
| `static/js/app.js:431-529` | `startRealtime()`, `stopRealtime()`, WebSocket handling |
| `static/js/app.js:1839-1890` | Orb toggle, pause, mute controls |
| `templates/index.html:399-416` | Orb HTML structure + controls |
