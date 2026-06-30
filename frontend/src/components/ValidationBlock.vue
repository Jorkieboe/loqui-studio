<script setup>
defineProps({
  errors: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="validation-block">
    <div class="vb-icon">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
      </svg>
    </div>
    <p class="vb-title">Chat unavailable</p>
    <p class="vb-subtitle">Fix the following to enable testing:</p>
    <ul class="vb-list">
      <li v-for="err in errors" :key="err" class="vb-item">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" class="vb-bullet">
          <circle cx="12" cy="12" r="5" />
        </svg>
        {{ err }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
.validation-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 2rem 1.5rem;
  text-align: center;
  background: #fff8f8;
  border-left: 1px solid var(--border);
}

.vb-icon {
  color: #DC2626;
  margin-bottom: 1rem;
  opacity: 0.85;
}

.vb-title {
  font-size: 1rem;
  font-weight: 700;
  color: #991B1B;
  margin-bottom: 0.3rem;
}

.vb-subtitle {
  font-size: 0.82rem;
  color: #7F1D1D;
  margin-bottom: 1.25rem;
  opacity: 0.8;
}

.vb-list {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.vb-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: #7F1D1D;
  background: #FEE2E2;
  border: 1px solid #FECACA;
  border-radius: 6px;
  padding: 0.45rem 0.65rem;
  line-height: 1.4;
}

.vb-bullet {
  flex-shrink: 0;
  margin-top: 3px;
  color: #DC2626;
}
</style>
