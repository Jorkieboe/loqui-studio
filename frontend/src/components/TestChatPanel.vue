<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  draftConfig: { type: Object, default: null },
})

const messages     = defineModel('messages',     { default: () => [] })
const sessionState = defineModel('sessionState', { default: () => ({ active_node_id: null, active_flow_id: 'main', open_topics: [], history: [], last_retrieved_chunks: [] }) })

const input   = ref('')
const loading = ref(false)
const chatEl  = ref(null)
const expandedIndex = ref(null)
const expandedPromptIndex = ref(null)
const copied = ref(false)

function toggleDebug(index) {
  expandedIndex.value = expandedIndex.value === index ? null : index
}

function togglePrompt(index) {
  expandedPromptIndex.value = expandedPromptIndex.value === index ? null : index
}

function getNodeName(nodeId) {
  if (!nodeId) return ''
  const node = props.draftConfig?.prompts?.var_prompt?.find(n => n.id === nodeId)
  return node?.displayName || node?.label || ''
}

function getAssistantNodeName(msg) {
  if (!msg.debug) return 'node'
  return msg.debug.step_name || getNodeName(msg.debug.step) || msg.debug.step || 'node'
}

async function copyLogs() {
  if (!messages.value.length) return

  const logLines = messages.value.map(msg => {
    if (msg.role === 'user') {
      return `[user]\n${msg.text}`
    } else if (msg.role === 'assistant') {
      const nodeName = getAssistantNodeName(msg)
      return `[assistant {${nodeName}}]\n${msg.text}`
    } else {
      return `[${msg.role}]\n${msg.text}`
    }
  })

  const fullLog = logLines.join('\n\n')

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(fullLog)
    } else {
      const textArea = document.createElement('textarea')
      textArea.value = fullLog
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
    }
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (err) {
    console.error('Failed to copy logs:', err)
  }
}

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
          active_flow_id: sessionState.value.active_flow_id || 'main',
          open_topics: sessionState.value.open_topics || [],
          history: sessionState.value.history,
          last_retrieved_chunks: sessionState.value.last_retrieved_chunks || [],
        },
        user_input: text,
      }),
    })

    const data = await res.json()

    if (!res.ok) {
      messages.value = [...messages.value, { role: 'assistant', text: data.detail || 'Unknown error', error: true }]
    } else {
      const debugPayload = data.debug || {
        character: data.character,
        step: data.step,
        step_name: data.step_name,
        pov: data.pov,
        chunks: data.chunks || [],
        active_flow_id: data.active_flow_id || 'main',
        open_topics: data.open_topics || [],
        intent: data.intent || 'resume_current_flow',
        dynamic_tools: data.dynamic_tools || [],
        rag_scheme: data.rag_scheme || null,
        rag_ext_info: data.rag_ext_info || 'disabled',
        rag_filters: data.rag_filters || {},
        rag_search_query: data.rag_search_query || '',
        system_prompt: data.system_prompt || '',
        user_payload: data.user_payload || '',
      }

      const warningMessages = (data.warnings || []).map(w => ({
        role: 'assistant',
        text: w,
        error: true,
      }))

      messages.value = [
        ...messages.value,
        ...warningMessages,
        {
          role: 'assistant',
          text: data.text,
          debug: debugPayload,
        }
      ]

      sessionState.value = {
        active_node_id: data.next_node_id,
        active_flow_id: data.debug?.active_flow_id || 'main',
        open_topics: data.debug?.open_topics || [],
        history: [...sessionState.value.history, { role: 'user', text }, { role: 'assistant', text: data.text }],
        last_retrieved_chunks: data.last_retrieved_chunks || data.retrieved_chunks || sessionState.value.last_retrieved_chunks || [],
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
  sessionState.value = { active_node_id: null, active_flow_id: 'main', open_topics: [], history: [], last_retrieved_chunks: [] }
  expandedIndex.value = null
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
      <div class="header-actions">
        <button
          class="copy-btn"
          @click="copyLogs"
          :title="copied ? 'Copied to clipboard!' : 'Copy log to clipboard'"
          :disabled="!messages.length"
        >
          <svg v-if="!copied" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
          <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#047857" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span>{{ copied ? 'Copied' : 'Copy log' }}</span>
        </button>
        <button class="reset-btn" @click="resetChat" title="Reset chat">↺</button>
      </div>
    </div>

    <div class="chat-messages" ref="chatEl">
      <div v-if="!messages.length" class="chat-empty">Type a message to test the character…</div>
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="message-item"
        :class="msg.role"
      >
        <div class="message" :class="msg.role">
          <div v-if="msg.role === 'assistant' && getAssistantNodeName(msg) !== 'node'" class="msg-node-tag">
            {{ getAssistantNodeName(msg) }}
          </div>
          <div
            class="bubble"
            :class="{ error: msg.error, 'has-debug': !!msg.debug }"
            @click="msg.debug ? toggleDebug(i) : null"
          >
            {{ msg.text }}
            <span v-if="msg.debug" class="debug-toggle-indicator">
              {{ expandedIndex === i ? '▲ hide info' : '▼ debug info' }}
            </span>
          </div>
        </div>

        <!-- Debug details drawer beneath the clicked message -->
        <div v-if="msg.debug && expandedIndex === i" class="debug-drawer">
          <div class="debug-row">
            <span class="debug-key">Character:</span>
            <span class="debug-val">{{ msg.debug.character || 'N/A' }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-key">Step:</span>
            <span class="debug-val step-tag">{{ msg.debug.step_name || getNodeName(msg.debug.step) || msg.debug.step || 'N/A' }}</span>
            <span v-if="msg.debug.step && (msg.debug.step_name || getNodeName(msg.debug.step)) !== msg.debug.step" class="debug-id-badge">#{{ msg.debug.step }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-key">Flow ID:</span>
            <span class="debug-val flow-tag">{{ msg.debug.active_flow_id || 'main' }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-key">Intent:</span>
            <span class="debug-val intent-tag">{{ msg.debug.intent || 'resume_current_flow' }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-key">POV:</span>
            <span class="debug-val">{{ msg.debug.pov === null ? 'None' : msg.debug.pov }}</span>
          </div>
          <div class="debug-row">
            <span class="debug-key">RAG Mode:</span>
            <span class="debug-val rag-mode-tag">{{ msg.debug.rag_ext_info || 'disabled' }}</span>
            <span v-if="msg.debug.rag_scheme" class="debug-id-badge">{{ msg.debug.rag_scheme }}</span>
          </div>
          <div v-if="msg.debug.rag_filters && Object.keys(msg.debug.rag_filters).length" class="debug-row debug-row-wrap">
            <span class="debug-key">Metadata Filter:</span>
            <span class="debug-val">
              {{ Object.entries(msg.debug.rag_filters).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`).join(' | ') }}
            </span>
          </div>
          <div v-if="msg.debug.rag_search_query" class="debug-row debug-row-wrap">
            <span class="debug-key">Search Query:</span>
            <span class="debug-val debug-query-text">{{ msg.debug.rag_search_query }}</span>
          </div>

          <div class="debug-sub-header">
            <span>Open Topics ({{ msg.debug.open_topics ? msg.debug.open_topics.length : 0 }}):</span>
          </div>
          <div v-if="!msg.debug.open_topics || !msg.debug.open_topics.length" class="debug-empty">
            None (no shelved topics)
          </div>
          <div v-else class="debug-topics-list">
            <div v-for="(topic, tIdx) in msg.debug.open_topics" :key="tIdx" class="debug-topic-item">
              <span class="topic-label">{{ topic.flow_label || topic.flow_id }}</span>
              <span class="topic-node">paused: {{ getNodeName(topic.paused_node_id) || topic.paused_node_id || 'N/A' }}</span>
            </div>
          </div>

          <div class="debug-sub-header">
            <span>Dynamic Tools ({{ msg.debug.dynamic_tools ? msg.debug.dynamic_tools.length : 0 }}):</span>
          </div>
          <div v-if="!msg.debug.dynamic_tools || !msg.debug.dynamic_tools.length" class="debug-empty">
            No dynamic tools
          </div>
          <div v-else class="debug-tools-list">
            <div v-for="(tool, toIdx) in msg.debug.dynamic_tools" :key="toIdx" class="debug-tool-item">
              <span class="tool-name">{{ tool.function?.name || tool.name }}</span>
              <span class="tool-desc">{{ tool.function?.description || tool.description }}</span>
            </div>
          </div>

          <div class="debug-chunks-header">
            <span>RAG Chunks ({{ msg.debug.chunks ? msg.debug.chunks.length : 0 }}):</span>
          </div>

          <div v-if="!msg.debug.chunks || !msg.debug.chunks.length" class="debug-empty">
            No chunks retrieved
          </div>

          <div v-else class="debug-chunks-list">
            <div v-for="(chunk, cIdx) in msg.debug.chunks" :key="cIdx" class="debug-chunk-box">
              <div class="chunk-id-tag">ID: {{ chunk.id || 'N/A' }}</div>
              <div class="chunk-body-text">{{ chunk.text }}</div>
            </div>
          </div>

          <div v-if="msg.debug.system_prompt || msg.debug.user_payload" class="debug-prompt-section">
            <button class="prompt-toggle-btn" @click.stop="togglePrompt(i)">
              {{ expandedPromptIndex === i ? '▲ Hide exact LLM prompt' : '▼ Show exact LLM prompt' }}
            </button>
            <div v-if="expandedPromptIndex === i" class="debug-prompt-box">
              <div v-if="msg.debug.system_prompt" class="prompt-part">
                <div class="prompt-part-label">System Prompt</div>
                <pre class="prompt-pre">{{ msg.debug.system_prompt }}</pre>
              </div>
              <div v-if="msg.debug.user_payload" class="prompt-part">
                <div class="prompt-part-label">User Payload (with injected RAG)</div>
                <pre class="prompt-pre">{{ msg.debug.user_payload }}</pre>
              </div>
            </div>
          </div>
        </div>
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.copy-btn {
  background: #f1f5f9;
  color: var(--text);
  border: 1px solid var(--border);
  font-size: 0.75rem;
  font-weight: 500;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.copy-btn:hover:not(:disabled) {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

.copy-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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

.msg-node-tag {
  font-size: 0.68rem;
  font-weight: 600;
  color: #4f46e5;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 4px;
  padding: 0.05rem 0.4rem;
  margin-bottom: 0.25rem;
  max-width: 85%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  flex-direction: column;
  align-items: flex-end;
}

.message-item {
  display: flex;
  flex-direction: column;
}

.bubble {
  max-width: 85%;
  padding: 0.6rem 0.9rem;
  border-radius: var(--radius);
  font-size: 0.88rem;
  line-height: 1.45;
  position: relative;
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

.bubble.has-debug {
  cursor: pointer;
  transition: box-shadow 0.15s, background-color 0.15s;
}

.bubble.has-debug:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.debug-toggle-indicator {
  display: block;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--primary-dark);
  text-align: right;
  margin-top: 0.35rem;
  opacity: 0.85;
}

.bubble.error {
  background: #ffe4e4;
  color: #c0392b;
}

/* ── Debug Drawer beneath the message ── */
.debug-drawer {
  background: #fdfdfd;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.6rem 0.75rem;
  margin-top: 0.4rem;
  font-size: 0.78rem;
  line-height: 1.4;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.debug-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.25rem;
}

.debug-key {
  font-weight: 600;
  color: var(--text-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
}

.debug-val {
  color: var(--text);
  font-weight: 500;
}

.step-tag {
  background: #eef2ff;
  color: #4f46e5;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  font-weight: 600;
}

.debug-id-badge {
  font-family: monospace;
  font-size: 0.68rem;
  color: var(--text-muted);
  background: #f1f5f9;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
}

.flow-tag {
  background: #f3e8ff;
  color: #7e22ce;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  font-family: monospace;
}

.intent-tag {
  background: #ecfdf5;
  color: #047857;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  font-family: monospace;
}

.rag-mode-tag {
  background: #e0f2fe;
  color: #0369a1;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  font-family: monospace;
}

.debug-row-wrap {
  align-items: flex-start;
  flex-wrap: wrap;
}

.debug-query-text {
  font-style: italic;
  word-break: break-word;
}

.debug-prompt-section {
  margin-top: 0.5rem;
  border-top: 1px dashed var(--border);
  padding-top: 0.4rem;
}

.prompt-toggle-btn {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  font-size: 0.72rem;
  font-weight: 600;
  width: 100%;
  text-align: left;
}

.prompt-toggle-btn:hover {
  background: #e2e8f0;
}

.debug-prompt-box {
  margin-top: 0.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.prompt-part-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 0.15rem;
}

.prompt-pre {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 0.45rem;
  font-family: monospace;
  font-size: 0.7rem;
  line-height: 1.35;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 220px;
  overflow-y: auto;
  margin: 0;
}

.debug-sub-header {
  font-weight: 600;
  color: var(--text-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
  margin-top: 0.5rem;
  margin-bottom: 0.25rem;
  border-top: 1px dashed var(--border);
  padding-top: 0.4rem;
}

.debug-topics-list,
.debug-tools-list {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-top: 0.25rem;
}

.debug-topic-item {
  background: #faf5ff;
  border: 1px solid #e9d5ff;
  border-radius: 4px;
  padding: 0.3rem 0.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.73rem;
}

.topic-label {
  font-weight: 600;
  color: #6b21a8;
}

.topic-node {
  font-family: monospace;
  font-size: 0.68rem;
  color: #9333ea;
}

.debug-tool-item {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 0.35rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.tool-name {
  font-family: monospace;
  font-weight: 700;
  font-size: 0.72rem;
  color: #0f172a;
}

.tool-desc {
  font-size: 0.7rem;
  color: var(--text-muted);
  line-height: 1.35;
}

.debug-chunks-header {
  font-weight: 600;
  color: var(--text-muted);
  font-size: 0.72rem;
  text-transform: uppercase;
  margin-top: 0.5rem;
  margin-bottom: 0.25rem;
  border-top: 1px dashed var(--border);
  padding-top: 0.4rem;
}

.debug-empty {
  color: var(--text-muted);
  font-style: italic;
  font-size: 0.75rem;
}

.debug-chunks-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 0.25rem;
}

.debug-chunk-box {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 0.4rem 0.55rem;
}

.chunk-id-tag {
  font-family: monospace;
  font-size: 0.68rem;
  font-weight: 600;
  color: #0284c7;
  margin-bottom: 0.2rem;
  word-break: break-all;
}

.chunk-body-text {
  font-size: 0.75rem;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
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