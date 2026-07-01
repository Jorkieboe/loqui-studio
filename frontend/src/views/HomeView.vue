<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getSessions, createSession } from '../utils/chatHistory'
import CharacterCard from '../components/CharacterCard.vue'

const router = useRouter()
const characters = ref([])
const sessions = ref([])

async function loadCharacters() {
  try {
    const res = await fetch('/api/characters')
    if (res.ok) characters.value = await res.json()
  } catch { /* offline */ }
}

async function loadSessions() {
  sessions.value = await getSessions()
}

async function startChat(char) {
  const session = await createSession(char.id, char.name, char.avatar || null)
  router.push(`/chat/${session.id}`)
}

function continueSession(session) {
  router.push(`/chat/${session.id}`)
}

const recentCharacters = computed(() => characters.value.slice(0, 5))

onMounted(() => {
  loadCharacters()
  loadSessions()
})
</script>

<template>
  <div class="home">
    <!-- Last used characters -->
    <section class="section">
      <h2 class="section-title">Lasted used:</h2>
      <div v-if="!characters.length" class="empty-hint">
        No characters yet. <router-link to="/characters">Create one →</router-link>
      </div>
      <div v-else class="character-row">
        <CharacterCard
          v-for="char in recentCharacters"
          :key="char.id"
          :char="char"
          :show-edit="false"
          class="char-card-sized"
          @click="startChat(char)"
        />
      </div>
    </section>

    <!-- History -->
    <section class="section">
      <h2 class="section-title">history</h2>
      <div v-if="!sessions.length" class="empty-hint">No chat history yet.</div>
      <div v-else class="history-grid">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="history-item"
          @click="continueSession(session)"
        >
          <!-- Avatar — full height of the card -->
          <div class="history-avatar">
            <img v-if="session.character_avatar" :src="session.character_avatar" :alt="session.character_name" />
            <div v-else class="history-avatar-placeholder">{{ (session.character_name || '?')[0] }}</div>
          </div>
          <!-- Text -->
          <div class="history-info">
            <div class="history-name">{{ session.character_name }}</div>
            <div class="history-preview">{{ session.last_message || 'No messages yet' }}</div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  padding: 2rem 2.5rem;
  overflow-y: auto;
  height: 100%;
}

.section {
  margin-bottom: 2.5rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 1.25rem;
  color: #2a2a2a;
}

/* ── CHARACTER ROW ── */
.character-row {
  display: flex;
  gap: 1.25rem;
}

/* Give the cards a fixed width; the component supplies aspect-ratio 3/4 */
.char-card-sized {
  width: 180px;
  flex-shrink: 0;
}

/* ── HISTORY GRID ── */
.history-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}

.history-item {
  display: flex;
  align-items: stretch; /* avatar fills full card height */
  background: white;
  border-radius: var(--radius);
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18);
  cursor: pointer;
  min-height: 88px;
  transition: box-shadow 0.15s;
}

.history-item:hover {
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.15);
}

/* Avatar — full height, fixed width, no extra padding */
.history-avatar {
  width: 80px;
  flex-shrink: 0;
  background: #d9d9d9;
  position: relative;
}

.history-avatar img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.history-avatar-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.5rem;
  color: var(--primary-dark);
  background: var(--primary-light);
}

/* Text content */
.history-info {
  flex: 1;
  min-width: 0;
  padding: 0.85rem 1rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.history-name {
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 0.3rem;
  color: #2a2a2a;
}

.history-preview {
  font-size: 0.85rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── EMPTY STATE ── */
.empty-hint {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.empty-hint a {
  color: var(--primary-dark);
  text-decoration: underline;
}
</style>
