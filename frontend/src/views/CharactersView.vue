<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { saveSession, createSessionId } from '../utils/chatHistory'
import CharacterCard from '../components/CharacterCard.vue'

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

function goToEditor(id) {
  router.push(`/characters/${id}/edit`)
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
      <div class="add-card" @click="goToNew">
        <span class="add-icon">+</span>
      </div>

      <!-- Character cards -->
      <CharacterCard
        v-for="char in characters"
        :key="char.id"
        :char="char"
        :show-edit="true"
        @click="goToChat(char)"
        @edit="goToEditor(char.id)"
      />
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

/* Add card keeps its own aspect-ratio and style */
.add-card {
  aspect-ratio: 3 / 4;
  border-radius: 10px;
  border: 2px dashed var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  cursor: pointer;
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
</style>
