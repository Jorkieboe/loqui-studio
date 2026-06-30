<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  draftConfig: { type: Object, default: null },
})

const messages     = defineModel('messages',     { default: () => [] })
const sessionState = defineModel('sessionState', { default: () => ({ active_node_id: null, history: [] }) })

const input   = ref('')
const loading = ref(false)
const chatEl  = ref(null)

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value = [...messages.value, { role: 'user', text }]
  input.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const res = await fetch('/api/characters/test-draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        draft_config: props.draftConfig,
        session_state: {
          active_node_id: sessionState.value.active_node_id,
          history: sessionState.value.history,
        },
        user_input: text,
      }),
    })

    const data = await res.json()

    if (!res.ok) {
      messages.value = [...messages.value, { role: 'assistant', text: `Error: ${data.detail || 'Unknown error'}`, error: true }]
    } else {
      messages.value = [...messages.value, { role: 'assistant', text: data.text }]
      sessionState.value = {
        active_node_id: data.next_node_id,
        history: [...sessionState.value.history, { role: 'user', text }, { role: 'assistant', text: data.text }],
      }
    }
  } catch (e) {
    messages.value = [...messages.value, { role: 'assistant', text: `Connection error: ${e.message}`, error: true }]
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function resetChat() {
  messages.value = []
  sessionState.value = { active_node_id: null, history: [] }
}

async function scrollToBottom() {
  await nextTick()
  if (chatEl.value) chatEl.value.scrollTop = chatEl.value.scrollHeight
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="test-chat">
    <div class="chat-header">
      <span>Test chat</span>
      <button class="reset-btn" @click="resetChat" title="Reset chat">↺</button>
    </div>

    <div class="chat-messages" ref="chatEl">
      <div v-if="!messages.length" class="chat-empty">Type a message to test the character…</div>
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message"
        :class="msg.role"
      >
        <div class="bubble" :class="{ error: msg.error }">{{ msg.text }}</div>
      </div>
      <div v-if="loading" class="message assistant">
        <div class="bubble typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <input
        v-model="input"
        type="text"
        placeholder="type here..."
        @keydown="onKeydown"
        :disabled="loading"
      />
      <button class="send-btn" @click="send" :disabled="loading || !input.trim()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M5 12H19M19 12L13 6M19 12L13 18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.test-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
}

.chat-header {
  padding: 0.75rem 1rem;
  font-weight: 600;
  font-size: 1rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.reset-btn {
  background: none;
  color: var(--text-muted);
  font-size: 1.2rem;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;
}

.reset-btn:hover {
  color: var(--text);
  background: var(--bg-light);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chat-empty {
  color: var(--text-muted);
  font-size: 0.85rem;
  text-align: center;
  margin-top: 2rem;
}

.message {
  display: flex;
}

.message.user {
  justify-content: flex-start;
}

.message.assistant {
  justify-content: flex-end;
}

.bubble {
  max-width: 85%;
  padding: 0.6rem 0.9rem;
  border-radius: var(--radius);
  font-size: 0.88rem;
  line-height: 1.45;
}

.message.user .bubble {
  background: white;
  border: 1px solid var(--border);
  color: var(--text);
}

.message.assistant .bubble {
  background: var(--primary-light);
  color: var(--text);
}

.bubble.error {
  background: #ffe4e4;
  color: #c0392b;
}

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

.chat-input {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem;
  border-top: 1px solid var(--border);
  background: var(--primary-light);
  flex-shrink: 0;
}

.chat-input input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0.4rem 0.25rem;
  font-size: 0.9rem;
  outline: none;
  color: var(--text);
}

.chat-input input::placeholder {
  color: var(--text-muted);
}

.send-btn {
  background: none;
  color: var(--primary);
  padding: 0.3rem;
  border-radius: 4px;
  display: flex;
  align-items: center;
  transition: color 0.15s;
}

.send-btn:hover:not(:disabled) {
  color: var(--primary-dark);
}

.send-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
