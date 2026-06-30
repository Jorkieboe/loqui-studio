<script setup>
import { useRoute } from 'vue-router'
import { useNavbarStore } from '../stores/navbar'

const route = useRoute()
const navbarStore = useNavbarStore()
</script>

<template>
  <nav class="navbar">
    <router-link to="/" class="brand">Loqui Studio</router-link>
    <div class="nav-links">
      <router-link
        to="/characters"
        class="nav-link"
        :class="{ active: route.path.startsWith('/characters') }"
      >
        Characters
      </router-link>
      <router-link
        to="/chat"
        class="nav-link"
        :class="{ active: route.path.startsWith('/chat') }"
      >
        Chat
      </router-link>
    </div>
    <div class="nav-actions">
      <button
        v-if="navbarStore.actionFn"
        class="nav-action-btn"
        @click="navbarStore.actionFn()"
      >
        {{ navbarStore.actionLabel }}
      </button>
    </div>
  </nav>
</template>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  padding: 0 2rem;
  height: var(--nav-height);
  background: var(--primary);
  gap: 2rem;
  flex-shrink: 0;
  z-index: 100;
}

.brand {
  font-weight: 700;
  font-size: 1.15rem;
  color: white;
  white-space: nowrap;
}

.nav-links {
  display: flex;
  gap: 1.5rem;
  flex: 1;
}

.nav-link {
  color: rgba(255,255,255,0.85);
  font-size: 0.95rem;
  transition: opacity 0.15s;
}

.nav-link:hover,
.nav-link.active {
  color: white;
  font-weight: 600;
}

.nav-actions {
  margin-left: auto;
}

.nav-action-btn {
  background: white;
  color: var(--text);
  padding: 0.4rem 1.2rem;
  border-radius: var(--radius);
  font-size: 0.9rem;
  font-weight: 500;
  transition: background 0.15s;
}

.nav-action-btn:hover {
  background: #f0f0f0;
}
</style>
