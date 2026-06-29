import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import CharactersView from '../views/CharactersView.vue'
import CharacterNewView from '../views/CharacterNewView.vue'
import CharacterEditorView from '../views/CharacterEditorView.vue'
import ChatView from '../views/ChatView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/characters', component: CharactersView },
    { path: '/characters/new', component: CharacterNewView },
    { path: '/characters/:id/edit', component: CharacterEditorView },
    { path: '/chat', component: ChatView },
    { path: '/chat/:id', component: ChatView },
  ],
})
