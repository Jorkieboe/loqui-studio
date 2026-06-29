<script setup>
import AppNavbar from './components/AppNavbar.vue'
</script>

<template>
  <div class="app">
    <AppNavbar />
    <div class="app-content">
      <router-view />
    </div>
  </div>
</template>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: #fff;
  color: #1a1a1a;
  line-height: 1.5;
}

:root {
  --primary: #3DCFAC;
  --primary-hover: #2db896;
  --primary-light: #C8EDE3;
  --primary-dark: #2AAB8A;
  --text: #1a1a1a;
  --text-muted: #888;
  --border: #e0e0e0;
  --bg-light: #f8f8f8;
  --nav-height: 56px;
  --radius: 8px;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.app-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

a { text-decoration: none; color: inherit; }

button {
  cursor: pointer;
  border: none;
  font-family: inherit;
}

input, textarea, select {
  font-family: inherit;
  font-size: 0.9rem;
}
</style>
