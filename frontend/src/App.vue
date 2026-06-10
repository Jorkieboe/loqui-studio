<template>
  <div class="app-container">
    <header class="app-header">
      <h1>New Parley</h1>
      <span class="status-badge" :class="{ connected: isConnected }">
        {{ isConnected ? 'Connected to Backend' : 'Disconnected' }}
      </span>
    </header>

    <main class="app-main">
      <section class="config-section">
        <h2>Backend Configuration Info</h2>
        <div v-if="loading" class="loader">Loading configuration...</div>
        <div v-else-if="error" class="error-msg">{{ error }}</div>
        <pre v-else class="config-display">{{ JSON.stringify(configData, null, 2) }}</pre>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';

export default {
  name: 'App',
  setup() {
    const configData = ref(null);
    const loading = ref(true);
    const error = ref(null);
    const isConnected = ref(false);

    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/config');
        if (!res.ok) {
          throw new Error(`Failed to fetch: ${res.statusText}`);
        }
        configData.value = await res.json();
        isConnected.value = true;
      } catch (err) {
        error.value = err.message;
        isConnected.value = false;
      } finally {
        loading.value = false;
      }
    };

    onMounted(() => {
      fetchConfig();
    });

    return {
      configData,
      loading,
      error,
      isConnected,
    };
  },
};
</script>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: #1a1a1a;
  color: #e0e0e0;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #2a2a2a;
  border-bottom: 1px solid #3a3a3a;
}

.app-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  background-color: #cf6679;
  color: #000;
  font-weight: bold;
}

.status-badge.connected {
  background-color: #03dac6;
}

.app-main {
  flex: 1;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.config-section {
  width: 100%;
  max-width: 600px;
  background-color: #2d2d2d;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
}

.config-section h2 {
  margin-top: 0;
  font-size: 1.2rem;
  border-bottom: 1px solid #444;
  padding-bottom: 0.5rem;
}

.loader {
  color: #aaa;
  font-style: italic;
}

.error-msg {
  color: #cf6679;
}

.config-display {
  background-color: #1e1e1e;
  padding: 1rem;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', Courier, monospace;
}
</style>