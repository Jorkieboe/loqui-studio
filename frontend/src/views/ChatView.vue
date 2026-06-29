<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { io } from 'socket.io-client'
import { getSessions, saveSession, createSessionId } from '../utils/chatHistory'

const route = useRoute()
const router = useRouter()

const sessionId = computed(() => route.params.id || null)
const sessions = ref([])
const currentSession = ref(null)
const messages = ref([])
const streamingText = ref('')
const inputText = ref('')
const voiceMode = ref(false)
const isRecording = ref(false)
const isWaiting = ref(false)

const chatEl = ref(null)
const textareaEl = ref(null)
let socket = null
let mediaRecorder = null
let audioChunks = []

const currentNodeId = ref('start')
const possibleNextNodes = ref([])
const sessionEnded = ref(false)

function loadSessions() {
  sessions.value = getSessions()
}

function loadSession(id) {
  const s = sessions.value.find(s => s.id === id)
  if (s) {
    currentSession.value = s
    messages.value = [...(s.history || [])]
    currentNodeId.value = s.currentNodeId || 'start'
  }
}

async function startNewChat(char) {
  const id = createSessionId()
  const session = {
    id,
    characterId: char.id,
    characterName: char.name,
    characterAvatar: char.avatar || null,
    history: [],
    lastMessage: '',
    timestamp: Date.now(),
    currentNodeId: 'start',
  }
  saveSession(session)
  loadSessions()
  router.push(`/chat/${id}`)
}

function persistSession() {
  if (!currentSession.value) return
  const updated = {
    ...currentSession.value,
    history: messages.value,
    lastMessage: messages.value.length ? messages.value[messages.value.length - 1].text.slice(0, 80) : '',
    timestamp: Date.now(),
    currentNodeId: currentNodeId.value,
  }
  saveSession(updated)
  loadSessions()
  currentSession.value = updated
}

function connectSocket() {
  if (socket) socket.disconnect()
  socket = io({ transports: ['websocket', 'polling'] })

  socket.on('response_chunk', (data) => {
    if (data?.text) streamingText.value += data.text
  })

  socket.on('response_complete', (data) => {
    if (streamingText.value) {
      messages.value.push({ role: 'assistant', text: streamingText.value })
      streamingText.value = ''
    }
    if (data?.next_node_id) currentNodeId.value = data.next_node_id
    if (data?.possible_next_nodes) possibleNextNodes.value = data.possible_next_nodes
    if (data?.session_ended) {
      sessionEnded.value = true
    }
    isWaiting.value = false
    persistSession()
    scrollToBottom()
  })

  socket.on('transcription', (data) => {
    if (data?.text) {
      messages.value.push({ role: 'user', text: data.text, isTranscription: true })
      scrollToBottom()
    }
  })

  socket.on('error', (err) => {
    messages.value.push({ role: 'system', text: `Error: ${err.detail || 'Unknown'}` })
    isWaiting.value = false
    scrollToBottom()
  })
}

function sendText() {
  const text = inputText.value.trim()
  if (!text || isWaiting.value || !currentSession.value || !socket) return

  messages.value.push({ role: 'user', text })
  inputText.value = ''
  isWaiting.value = true
  scrollToBottom()

  socket.emit('chat_message', {
    character_id: currentSession.value.characterId,
    text,
    active_node_id: currentNodeId.value,
    history: messages.value.slice(0, -1),
  })
}

async function startRecording() {
  if (isRecording.value || !navigator.mediaDevices) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data) }
    mediaRecorder.onstop = sendAudio
    mediaRecorder.start()
    isRecording.value = true
  } catch (e) {
    messages.value.push({ role: 'system', text: 'Microphone access denied.' })
  }
}

function stopRecording() {
  if (!isRecording.value || !mediaRecorder) return
  mediaRecorder.stop()
  mediaRecorder.stream.getTracks().forEach(t => t.stop())
  isRecording.value = false
}

function sendAudio() {
  if (!audioChunks.length || !socket || !currentSession.value) return
  const blob = new Blob(audioChunks, { type: 'audio/webm' })
  const reader = new FileReader()
  reader.onload = () => {
    isWaiting.value = true
    socket.emit('audio_message', {
      audio: reader.result,
      character_id: currentSession.value.characterId,
      active_node_id: currentNodeId.value,
      history: messages.value,
    })
  }
  reader.readAsArrayBuffer(blob)
}

function resetSession() {
  sessionEnded.value = false
  currentNodeId.value = 'start'
  possibleNextNodes.value = []
}

function growTextarea() {
  const el = textareaEl.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 140) + 'px'
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendText()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
}

function formatTime(ts) {
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'now'
  if (diffMins < 60) return `${diffMins}m`
  return `${Math.floor(diffMins / 60)}h`
}

watch(() => route.params.id, (id) => {
  messages.value = []
  streamingText.value = ''
  sessionEnded.value = false
  if (id) loadSession(id)
}, { immediate: true })

onMounted(() => {
  loadSessions()
  connectSocket()
  if (sessionId.value) loadSession(sessionId.value)
})

onBeforeUnmount(() => {
  if (socket) socket.disconnect()
  if (mediaRecorder && isRecording.value) stopRecording()
})
</script>

<template>
  <div class="chat-view">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sidebar-title">Chat history</div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="router.push(`/chat/${s.id}`)"
        >
          <div class="session-avatar">
            <img v-if="s.characterAvatar" :src="s.characterAvatar" :alt="s.characterName" />
            <div v-else class="session-avatar-ph">{{ (s.characterName || '?')[0] }}</div>
          </div>
          <div class="session-info">
            <div class="session-name">{{ s.characterName }}</div>
            <div class="session-preview">{{ s.lastMessage || 'No messages' }}</div>
          </div>
        </div>
        <div v-if="!sessions.length" class="sidebar-empty">
          No history yet.
        </div>
      </div>
    </aside>

    <!-- MAIN CHAT -->
    <div class="chat-main">
      <div v-if="!currentSession" class="no-session">
        <p>Select a conversation or <router-link to="/">start a new one</router-link>.</p>
      </div>

      <template v-else>
        <div class="chat-topbar">
          <h2 class="char-name">{{ currentSession.characterName || 'Character' }}</h2>
          <div class="voice-toggle">
            <span>voice mode:</span>
            <button
              class="toggle"
              :class="{ on: voiceMode }"
              @click="voiceMode = !voiceMode"
              :aria-label="voiceMode ? 'Disable voice mode' : 'Enable voice mode'"
            >
              <span class="toggle-knob"></span>
            </button>
          </div>
        </div>

        <div class="chat-body">
          <!-- Scrollable messages -->
          <div class="chat-messages" ref="chatEl">
            <template v-for="(msg, i) in messages" :key="i">
              <!-- CHARACTER message — LEFT -->
              <div v-if="msg.role === 'assistant'" class="message-row assistant">
                <div class="avatar-thumb">
                  <img v-if="currentSession.characterAvatar" :src="currentSession.characterAvatar" alt="" />
                  <div v-else class="char-thumb">{{ (currentSession.characterName || '?')[0] }}</div>
                </div>
                <div class="bubble assistant-bubble">{{ msg.text }}</div>
              </div>

              <!-- USER message — RIGHT -->
              <div v-else-if="msg.role === 'user'" class="message-row user">
                <div class="bubble user-bubble">{{ msg.text }}</div>
                <div class="avatar-thumb user-thumb-wrap">
                  <div class="user-thumb-inner"></div>
                </div>
              </div>

              <!-- SYSTEM message — CENTER -->
              <div v-else class="message-row system">
                <div class="bubble system-bubble">{{ msg.text }}</div>
              </div>
            </template>

            <!-- Streaming response — LEFT -->
            <div v-if="streamingText" class="message-row assistant">
              <div class="avatar-thumb">
                <img v-if="currentSession.characterAvatar" :src="currentSession.characterAvatar" alt="" />
                <div v-else class="char-thumb">{{ (currentSession.characterName || '?')[0] }}</div>
              </div>
              <div class="bubble assistant-bubble streaming">{{ streamingText }}</div>
            </div>

            <!-- Typing indicator — LEFT -->
            <div v-if="isWaiting && !streamingText" class="message-row assistant">
              <div class="avatar-thumb">
                <img v-if="currentSession.characterAvatar" :src="currentSession.characterAvatar" alt="" />
                <div v-else class="char-thumb">{{ (currentSession.characterName || '?')[0] }}</div>
              </div>
              <div class="bubble assistant-bubble typing">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>

          <!-- Floating input area (gradient + bar) -->
          <div class="input-float">
            <div v-if="sessionEnded" class="session-ended">
              <span>Conversation ended.</span>
              <button @click="resetSession">Start over</button>
            </div>

            <!-- TEXT INPUT -->
            <div v-if="!voiceMode" class="input-wrap">
              <div class="input-inner" :class="{ disabled: isWaiting || sessionEnded }">
                <textarea
                  ref="textareaEl"
                  v-model="inputText"
                  placeholder="type here..."
                  @keydown="onKeydown"
                  @input="growTextarea"
                  :disabled="isWaiting || sessionEnded"
                  maxlength="300"
                  rows="1"
                />
                <button
                  class="send-btn"
                  @click="sendText"
                  :disabled="isWaiting || !inputText.trim() || sessionEnded"
                >
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                    <path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </div>
              <div v-if="inputText.length > 240" class="char-count" :class="{ warn: inputText.length >= 290 }">
                {{ 300 - inputText.length }} left
              </div>
            </div>

            <!-- VOICE INPUT -->
            <div v-else class="voice-wrap">
              <button
                class="mic-btn"
                :class="{ recording: isRecording }"
                @mousedown="startRecording"
                @mouseup="stopRecording"
                @touchstart.prevent="startRecording"
                @touchend.prevent="stopRecording"
                :disabled="isWaiting || sessionEnded"
                title="Hold to record"
              >
                <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 1a4 4 0 0 1 4 4v6a4 4 0 1 1-8 0V5a4 4 0 0 1 4-4zm0 16a7 7 0 0 0 7-7h-1.5A5.5 5.5 0 0 1 12 15.5 5.5 5.5 0 0 1 6.5 10H5a7 7 0 0 0 7 7zm-1 2h2v2h-2v-2z"/>
                </svg>
              </button>
              <div class="mic-label">{{ isRecording ? 'Recording… release to send' : 'Hold to speak' }}</div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ── SIDEBAR ── */
.sidebar {
  width: 260px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  background: white;
}

.sidebar-title {
  padding: 1rem 1.25rem;
  font-weight: 700;
  font-size: 1.1rem;
  border-bottom: 1px solid var(--border);
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  display: flex;
  gap: 0.65rem;
  align-items: flex-start;
  padding: 0.85rem 1.25rem;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid var(--border);
}

.session-item:hover,
.session-item.active {
  background: var(--bg-light);
}

.session-avatar {
  width: 60px;
  height: 60px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg-light);
}

.session-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.session-avatar-ph {
  width: 100%;
  height: 100%;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--primary-dark);
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 0.2rem;
}

.session-preview {
  font-size: 0.82rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-empty {
  padding: 1rem 1.25rem;
  color: var(--text-muted);
  font-size: 0.85rem;
}

/* ── MAIN CHAT ── */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.no-session {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 0.95rem;
}

.no-session a {
  color: var(--primary-dark);
  text-decoration: underline;
}

.chat-topbar {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.char-name {
  font-size: 2rem;
  font-weight: 700;
  flex: 1;
}

.voice-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: var(--text-muted);
}

.toggle {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: var(--border);
  position: relative;
  transition: background 0.2s;
  flex-shrink: 0;
}

.toggle.on {
  background: var(--primary);
}

.toggle-knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.toggle.on .toggle-knob {
  transform: translateX(20px);
}

/* ── CHAT BODY (messages + floating input) ── */
.chat-body {
  flex: 1;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── MESSAGES ── */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 2rem 200px; /* bottom padding clears the floating bar */
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.message-row.assistant { justify-content: flex-start; }
.message-row.user      { justify-content: flex-end; }
.message-row.system    { justify-content: center; }

.bubble {
  max-width: 55%;
  padding: 0.7rem 1rem;
  border-radius: var(--radius);
  font-size: 0.92rem;
  line-height: 1.55;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}

.assistant-bubble {
  background: white;
  border: 1px solid rgba(0,0,0,0.12);
}

.user-bubble {
  background: rgba(29, 196, 149, 0.2);
}

.system-bubble {
  background: var(--bg-light);
  color: var(--text-muted);
  font-size: 0.82rem;
  border-radius: 20px;
  max-width: none;
  box-shadow: none;
}

.streaming { font-style: italic; opacity: 0.85; }

.typing {
  display: flex;
  gap: 5px;
  align-items: center;
  padding: 0.75rem 1rem;
}

.typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--primary);
  animation: bounce 1s infinite;
}
.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

.avatar-thumb {
  width: 44px;
  height: 44px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.avatar-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.char-thumb {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.95rem;
  background: var(--primary-light);
  color: var(--primary-dark);
}

.user-thumb-wrap { background: #d9d9d9; }
.user-thumb-inner { width: 100%; height: 100%; background: #d9d9d9; }

/* ── FLOATING INPUT ── */
.input-float {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  /* White gradient fades messages out behind the bar */
  background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,0.85) 28%, white 52%);
  padding-top: 3.5rem;
  padding-bottom: 1.25rem;
  pointer-events: none; /* let scroll pass through the gradient zone */
}

.input-float > * {
  pointer-events: all; /* re-enable for actual controls */
}

/* Session ended */
.session-ended {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.5rem 0 0.75rem;
  font-size: 0.88rem;
  color: var(--text-muted);
}

.session-ended button {
  background: var(--primary);
  color: white;
  padding: 0.3rem 0.9rem;
  border-radius: var(--radius);
  font-size: 0.85rem;
  transition: background 0.15s;
}

.session-ended button:hover { background: var(--primary-hover); }

/* Input wrapper — centred, max-width */
.input-wrap {
  max-width: 600px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

/* Teal pill */
.input-inner {
  display: flex;
  align-items: flex-end;
  background: rgba(29, 196, 149, 0.18);
  border-radius: 10px;
  padding: 0.5rem 0.5rem 0.5rem 0.75rem;
  gap: 0.5rem;
}

.input-inner.disabled { opacity: 0.6; }

.input-inner textarea {
  flex: 1;
  border: none;
  background: #f7f5f5;
  padding: 0.55rem 0.75rem;
  font-size: 0.95rem;
  outline: none;
  color: var(--text);
  border-radius: 6px;
  resize: none;
  line-height: 1.5;
  font-family: inherit;
  min-height: 38px;
  max-height: 140px;
  overflow-y: auto;
}

.input-inner textarea::placeholder { color: #aaa; }

.send-btn {
  background: none;
  color: var(--primary);
  padding: 0.35rem 0.4rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  transition: color 0.15s;
  /* align with bottom of textarea */
  margin-bottom: 2px;
}

.send-btn:hover:not(:disabled) { color: var(--primary-dark); }
.send-btn:disabled { opacity: 0.35; cursor: not-allowed; }

.char-count {
  text-align: right;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.3rem;
  padding-right: 0.25rem;
}

.char-count.warn { color: #e53e3e; }

/* ── VOICE BAR ── */
.voice-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.mic-btn {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--primary);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, transform 0.1s;
  user-select: none;
}

.mic-btn:hover:not(:disabled) {
  background: var(--primary-hover);
}

.mic-btn.recording {
  background: #e53e3e;
  transform: scale(1.08);
}

.mic-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.mic-label {
  font-size: 0.8rem;
  color: var(--text-muted);
}
</style>
