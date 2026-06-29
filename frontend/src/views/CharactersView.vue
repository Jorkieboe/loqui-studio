<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { saveSession, createSessionId } from '../utils/chatHistory'

const router = useRouter()
const characters = ref([])

async function loadCharacters() {
  try {
    const res = await fetch('/api/characters')
    if (res.ok) characters.value = await res.json()
  } catch { /* offline */ }
}

function goToChat(char) {
  const sessionId = createSessionId()
  saveSession({
    id: sessionId,
    characterId: char.id,
    characterName: char.name,
    characterAvatar: char.avatar || null,
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  })
  router.push(`/chat/${sessionId}`)
}

function goToEditor(char, e) {
  e.stopPropagation()
  router.push(`/characters/${char.id}/edit`)
}

function goToNew() {
  router.push('/characters/new')
}

onMounted(loadCharacters)
</script>

<template>
  <div class="characters-page">
    <h1 class="page-title">Characters</h1>
    <div class="character-grid">
      <!-- Add new card -->
      <div class="char-card add-card" @click="goToNew">
        <span class="add-icon">+</span>
      </div>

      <!-- Character cards -->
      <div
        v-for="char in characters"
        :key="char.id"
        class="char-card"
        @click="goToChat(char)"
      >
        <!-- Background image or placeholder -->
        <img v-if="char.avatar" :src="char.avatar" :alt="char.name" class="card-img" />
        <div v-else class="card-placeholder">{{ char.name[0] }}</div>

        <!-- Gradient overlays -->
        <div class="overlay-idle"></div>
        <div class="overlay-hover"></div>

        <!-- Edit icon — always visible -->
        <button class="edit-btn" @click="goToEditor(char, $event)" title="Edit character">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </button>

        <!-- Name + description -->
        <div class="card-info">
          <div class="card-name">{{ char.name }}</div>
          <div v-if="char.description" class="card-desc">{{ char.description }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.characters-page {
  padding: 2rem 2.5rem;
  overflow-y: auto;
  height: 100%;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 1.75rem;
  color: #2a2a2a;
}

.character-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.25rem;
}

/* ── BASE CARD ── */
.char-card {
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  position: relative;
  aspect-ratio: 3 / 4;
  background: var(--bg-light);
}

/* ── ADD CARD ── */
.add-card {
  border: 2px dashed var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: border-color 0.2s, background 0.2s;
}

.add-card:hover {
  border-color: var(--primary);
  background: var(--primary-light);
}

.add-icon {
  font-size: 3rem;
  color: var(--text-muted);
  line-height: 1;
  transition: color 0.2s;
}

.add-card:hover .add-icon {
  color: var(--primary-dark);
}

/* ── IMAGE ── */
.card-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.card-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  font-weight: 700;
  background: var(--primary-light);
  color: var(--primary-dark);
}

/* ── GRADIENT OVERLAYS ── */
/* Idle: gradient from 80% to 100% — always present */
.overlay-idle {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 80%, rgba(0, 0, 0, 0.88) 100%);
  border-radius: inherit;
  transition: opacity 0.3s ease;
}

/* Hover: wider gradient from 60% to 100% — fades in on hover */
.overlay-hover {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 60%, rgba(0, 0, 0, 0.55) 80%, rgba(0, 0, 0, 0.88) 100%);
  border-radius: inherit;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.char-card:hover .overlay-hover {
  opacity: 1;
}

/* ── EDIT BUTTON ── */
.edit-btn {
  position: absolute;
  top: 0.6rem;
  right: 0.6rem;
  z-index: 3;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  color: var(--primary-dark);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.25);
  opacity: 0.7;
  transition: opacity 0.2s, transform 0.15s, background 0.15s;
}

.char-card:hover .edit-btn {
  opacity: 1;
}

.edit-btn:hover {
  transform: scale(1.12);
  background: white;
}

/* ── TEXT INFO ── */
.card-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 2;
  padding: 0.85rem 0.9rem 0.9rem;
  color: white;
}

.card-name {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.25;
}

.card-desc {
  font-size: 0.82rem;
  margin-top: 0.3rem;
  line-height: 1.4;
  opacity: 0;
  max-height: 0;
  overflow: hidden;
  transition: opacity 0.3s ease, max-height 0.3s ease;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.char-card:hover .card-desc {
  opacity: 0.9;
  max-height: 56px;
}
</style>
