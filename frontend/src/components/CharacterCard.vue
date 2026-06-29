<script setup>
defineProps({
  char: { type: Object, required: true },
  showEdit: { type: Boolean, default: false },
})

defineEmits(['click', 'edit'])
</script>

<template>
  <div class="char-card" @click="$emit('click')">
    <!-- Background image / placeholder -->
    <img v-if="char.avatar" :src="char.avatar" :alt="char.name" class="card-img" />
    <div v-else class="card-placeholder">{{ char.name[0] }}</div>

    <!-- Gradient overlays -->
    <div class="overlay-idle"></div>
    <div class="overlay-hover"></div>

    <!-- Edit button (optional) -->
    <button v-if="showEdit" class="edit-btn" @click.stop="$emit('edit')" title="Edit character">
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
</template>

<style scoped>
.char-card {
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  position: relative;
  aspect-ratio: 3 / 4;
  background: var(--bg-light);
}

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

/* Idle gradient: transparent 80% → dark 100% */
.overlay-idle {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 80%, rgba(0, 0, 0, 0.88) 100%);
  border-radius: inherit;
}

/* Hover gradient: fades in, starts earlier at 60% */
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

/* Edit button */
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

/* Name + description overlay */
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
