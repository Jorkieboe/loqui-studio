<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getSessions, createSessionId, saveSession } from '../utils/chatHistory'

const router = useRouter()

const characters = ref([])
const sessions = ref([])

async function loadCharacters() {
  try {
    const res = await fetch('/api/characters')
    if (res.ok) characters.value = await res.json()
  } catch { /* backend offline */ }
}

function loadSessions() {
  sessions.value = getSessions()
}

function getAvatarUrl(char) {
  return char.avatar || null
}

function startChat(char) {
  const id = createSessionId()
  saveSession({
    id,
    characterId: char.id,
    characterName: char.name,
    characterAvatar: char.avatar || null,
    history: [],
    lastMessage: '',
    timestamp: Date.now(),
  })
  router.push(`/chat/${id}`)
}

function continueSession(session) {
  router.push(`/chat/${session.id}`)
}

function formatTime(ts) {
  const d = new Date(ts)
  const now = new Date()
  const diffMs = now - d
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return d.toLocaleDateString()
}

const recentCharacters = computed(() => characters.value.slice(0, 5))

onMounted(() => {
  loadCharacters()
  loadSessions()
})
</script>

<template>
  <div class="home">
    <section class="section">
      <h2 class="section-title">Lasted used:</h2>
      <div class="character-row">
        <div
          v-for="char in recentCharacters"
          :key="char.id"
          class="char-card"
          @click="startChat(char)"
        >
          <div class="char-avatar">
            <img v-if="char.avatar" :src="char.avatar" :alt="char.name" />
            <div v-else class="char-avatar-placeholder">{{ char.name[0] }}</div>
          </div>
          <div class="char-name">{{ char.name }}</div>
        </div>
        <div v-if="!characters.length" class="empty-hint">
          No characters yet. <router-link to="/characters">Create one →</router-link>
        </div>
      </div>
    </section>

    <section class="section">
      <h2 class="section-title">history</h2>
      <div v-if="!sessions.length" class="empty-hint">No chat history yet.</div>
      <div class="history-grid">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="history-item"
          @click="continueSession(session)"
        >
          <div class="history-avatar">
            <img v-if="session.characterAvatar" :src="session.characterAvatar" :alt="session.characterName" />
            <div v-else class="history-avatar-placeholder">{{ (session.characterName || '?')[0] }}</div>
          </div>
          <div class="history-info">
            <div class="history-name">{{ session.characterName }}</div>
            <div class="history-preview">{{ session.lastMessage || 'No messages yet' }}</div>
          </div>
          <div class="history-time">{{ formatTime(session.timestamp) }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  padding: 2rem;
  overflow-y: auto;
  height: 100%;
}

.section {
  margin-bottom: 2.5rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 1.25rem;
}

.character-row {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.char-card {
  position: relative;
  width: 220px;
  height: 220px;
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  flex-shrink: 0;
}

.char-card:hover .char-avatar img,
.char-card:hover .char-avatar-placeholder {
  transform: scale(1.03);
}

.char-avatar {
  width: 100%;
  height: 100%;
}

.char-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.2s;
  display: block;
}

.char-avatar-placeholder {
  width: 100%;
  height: 100%;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  font-weight: 700;
  color: var(--primary-dark);
  transition: transform 0.2s;
}

.char-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.4rem 0.75rem;
  background: rgba(0,0,0,0.45);
  color: white;
  font-size: 0.9rem;
  font-weight: 500;
}

.history-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: background 0.15s;
}

.history-item:hover {
  background: var(--bg-light);
}

.history-avatar {
  width: 48px;
  height: 48px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
  background: var(--bg-light);
}

.history-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.history-avatar-placeholder {
  width: 100%;
  height: 100%;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--primary-dark);
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-name {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.2rem;
}

.history-preview {
  font-size: 0.82rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-time {
  font-size: 0.75rem;
  color: var(--text-muted);
  flex-shrink: 0;
}

.empty-hint {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.empty-hint a {
  color: var(--primary-dark);
  text-decoration: underline;
}
</style>
