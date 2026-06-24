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

      <section class="chat-section">
        <h2>Socket.IO Interactive Chat</h2>
        <div class="connection-status">
          Socket Connection:
          <span :class="socketConnected ? 'text-success' : 'text-danger'">
            {{ socketConnected ? 'Connected' : 'Disconnected' }}
          </span>
          <br />
          Current Node: <span class="text-success">{{ currentNodeId }}</span>
          <span v-if="possibleNextNodes.length"> | Next Choices: {{ possibleNextNodes.join(', ') }}</span>
        </div>

        <div class="chat-box">
          <div v-for="(msg, idx) in chatHistory" :key="idx" class="message" :class="msg.role">
            <strong>{{ msg.role === 'user' ? 'You' : 'Character' }}:</strong> {{ msg.text }}
          </div>
          <div v-if="streamingText" class="message assistant streaming">
            <strong>Character (typing):</strong> {{ streamingText }}
          </div>
        </div>

        <div class="input-container">
          <input
            v-model="inputMessage"
            @keyup.enter="sendMessage"
            placeholder="Type a message to the historical character..."
            :disabled="!socketConnected"
          />
          <button @click="sendMessage" :disabled="!socketConnected || !inputMessage.trim()">
            Send
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { io } from 'socket.io-client';

export default {
  name: 'App',
  setup() {
    const configData = ref(null);
    const loading = ref(true);
    const error = ref(null);
    const isConnected = ref(false);

    const socketConnected = ref(false);
    const chatHistory = ref([]);
    const inputMessage = ref('');
    const streamingText = ref('');
    const currentNodeId = ref('start');
    const possibleNextNodes = ref([]);
    let socket = null;

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

    const sendMessage = () => {
      if (!inputMessage.value.trim() || !socketConnected.value) return;

      const userText = inputMessage.value.trim();
      chatHistory.value.push({ role: 'user', text: userText });
      inputMessage.value = '';
      streamingText.value = '';

      socket.emit('chat_message', {
        character_id: 'werker',
        text: userText,
        active_node_id: currentNodeId.value,
        history: chatHistory.value.slice(0, -1)
      });
    };

    onMounted(() => {
      fetchConfig();

      socket = io({
        transports: ['websocket', 'polling']
      });

      socket.on('connect', () => {
        socketConnected.value = true;
      });

      socket.on('disconnect', () => {
        socketConnected.value = false;
      });

      socket.on('response_chunk', (data) => {
        if (data && data.text) {
          streamingText.value += data.text;
        }
      });

      socket.on('response_complete', (data) => {
        if (streamingText.value) {
          chatHistory.value.push({ role: 'assistant', text: streamingText.value });
          streamingText.value = '';
        }
        if (data && data.next_node_id) {
          currentNodeId.value = data.next_node_id;
        }
        if (data && data.possible_next_nodes) {
          possibleNextNodes.value = data.possible_next_nodes;
        }
        if (data && data.session_ended) {
          alert("Dialogue session has completed. Resetting conversational playground.");
          chatHistory.value = [];
          currentNodeId.value = 'start';
          possibleNextNodes.value = [];
        }
      });

      socket.on('error', (err) => {
        console.error('Socket communication pipeline error:', err);
      });
    });

    onBeforeUnmount(() => {
      if (socket) {
        socket.disconnect();
      }
    });

    return {
      configData,
      loading,
      error,
      isConnected,
      socketConnected,
      chatHistory,
      inputMessage,
      streamingText,
      currentNodeId,
      possibleNextNodes,
      sendMessage,
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

.chat-section {
  width: 100%;
  max-width: 600px;
  background-color: #2d2d2d;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  margin-top: 2rem;
}

.chat-section h2 {
  margin-top: 0;
  font-size: 1.2rem;
  border-bottom: 1px solid #444;
  padding-bottom: 0.5rem;
}

.connection-status {
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.text-success {
  color: #03dac6;
  font-weight: bold;
}

.text-danger {
  color: #cf6679;
  font-weight: bold;
}

.chat-box {
  background-color: #1e1e1e;
  border: 1px solid #3a3a3a;
  border-radius: 4px;
  height: 250px;
  overflow-y: auto;
  padding: 1rem;
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.message {
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  max-width: 85%;
  font-size: 0.95rem;
  line-height: 1.4;
}

.message.user {
  background-color: #3a3a3a;
  color: #ffffff;
  align-self: flex-end;
}

.message.assistant {
  background-color: #1a2c3a;
  color: #e0e0e0;
  align-self: flex-start;
  border-left: 3px solid #03dac6;
}

.message.streaming {
  opacity: 0.85;
  font-style: italic;
}

.input-container {
  display: flex;
  gap: 0.5rem;
}

.input-container input {
  flex: 1;
  background-color: #1e1e1e;
  border: 1px solid #3a3a3a;
  color: #e0e0e0;
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
}

.input-container button {
  background-color: #03dac6;
  border: none;
  color: #000;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}

.input-container button:disabled {
  background-color: #444;
  color: #888;
  cursor: not-allowed;
}
</style>