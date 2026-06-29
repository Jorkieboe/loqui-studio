<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const characters = ref([])
const hoveredId = ref(null)

async function loadCharacters() {
  try {
    const res = await fetch('/api/characters')
    if (res.ok) characters.value = await res.json()
  } catch { /* offline */ }
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
      <div class="char-card add-card" @click="goToNew">
        <span class="add-icon">+</span>
      </div>
      <div
        v-for="char in characters"
        :key="char.id"
        class="char-card"
        @mouseenter="hoveredId = char.id"
        @mouseleave="hoveredId = null"
        @click="goToEditor(char.id)"
      >
        <div class="card-image">
          <img v-if="char.avatar" :src="char.avatar" :alt="char.name" />
          <div v-else class="avatar-placeholder">{{ char.name[0] }}</div>
          <button
            v-if="hoveredId === char.id"
            class="edit-btn"
            @click.stop="goToEditor(char.id)"
            title="Edit character"
          >
            ✏️
          </button>
        </div>
        <div class="card-footer">
          <div class="card-name">{{ char.name }}</div>
          <div v-if="char.description" class="card-desc">{{ char.description }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.characters-page {
  padding: 2rem;
  overflow-y: auto;
  height: 100%;
}

.page-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
}

.character-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.char-card {
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  position: relative;
  aspect-ratio: 3/4;
}

.add-card {
  border: 2px dashed var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  transition: border-color 0.15s, background 0.15s;
}

.add-card:hover {
  border-color: var(--primary);
  background: var(--primary-light);
}

.add-icon {
  font-size: 2.5rem;
  color: var(--text-muted);
  line-height: 1;
}

.add-card:hover .add-icon {
  color: var(--primary-dark);
}

.card-image {
  position: relative;
  width: 100%;
  height: 100%;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 4rem;
  font-weight: 700;
  color: var(--primary-dark);
}

.edit-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: white;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  transition: transform 0.15s;
}

.edit-btn:hover {
  transform: scale(1.1);
}

.card-footer {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0.5rem 0.75rem;
  background: linear-gradient(transparent, rgba(0,0,0,0.6));
  color: white;
}

.card-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.card-desc {
  font-size: 0.78rem;
  opacity: 0.85;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
