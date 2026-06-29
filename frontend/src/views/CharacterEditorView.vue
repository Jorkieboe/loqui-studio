<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TestChatPanel from '../components/TestChatPanel.vue'
import GraphEditor from '../components/GraphEditor.vue'
import { useNavbarStore } from '../stores/navbar'

const route = useRoute()
const router = useRouter()
const navbarStore = useNavbarStore()

const charId = computed(() => route.params.id)
const activeTab = ref('base')

const info = ref({
  id: '',
  name: '',
  description: '',
  tags: [],
  language: 'en',
  color: '#3DCFAC',
  idle_timeout_seconds: 300,
  rag: { ragScheme: '', pov: '', chunksize: 4 },
})

const prompts = ref({
  base_prompt: '',
  do: [''],
  "don't": [''],
  context: { setting: '', personality: '', background: '', role: '' },
  var_prompt: [],
})

const layout = ref({ nodes: [], connections: [] })

const avatarPreview = ref(null)
const avatarFile = ref(null)
const saving = ref(false)
const loading = ref(true)
const saveError = ref('')

const selectedNodeLabel = ref(null)
const selectedPromptNode = computed(() => {
  if (!selectedNodeLabel.value) return null
  return prompts.value.var_prompt?.find(p => p.id === selectedNodeLabel.value) || null
})

async function loadCharacter() {
  loading.value = true
  try {
    const res = await fetch(`/api/characters/item/${charId.value}`)
    if (!res.ok) throw new Error('Not found')
    const data = await res.json()
    info.value = { ...info.value, ...data.info }
    if (data.prompts) {
      prompts.value = {
        base_prompt: data.prompts.base_prompt || '',
        do: data.prompts.do?.length ? data.prompts.do : [''],
        "don't": data.prompts["don't"]?.length ? data.prompts["don't"] : [''],
        context: { setting: '', personality: '', background: '', role: '', ...data.prompts.context },
        var_prompt: data.prompts.var_prompt || [],
      }
    }
    if (data.layout) {
      layout.value = { nodes: data.layout.nodes || [], connections: data.layout.connections || [] }
    }
    if (data.info?.avatar) {
      avatarPreview.value = data.info.avatar
    }
  } catch (e) {
    saveError.value = e.message
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  saveError.value = ''
  try {
    const res = await fetch(`/api/characters/item/${charId.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ info: info.value, prompts: prompts.value, layout: layout.value }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Save failed')
    }
    if (avatarFile.value) {
      const form = new FormData()
      form.append('file', avatarFile.value)
      await fetch(`/api/characters/item/${charId.value}/avatar`, { method: 'POST', body: form })
    }
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

function onAvatarChange(e) {
  const file = e.target.files[0]
  if (!file) return
  avatarFile.value = file
  avatarPreview.value = URL.createObjectURL(file)
}

function addDo() { prompts.value.do.push('') }
function removeDo(i) { if (prompts.value.do.length > 1) prompts.value.do.splice(i, 1) }
function addDont() { prompts.value["don't"].push('') }
function removeDont(i) { if (prompts.value["don't"].length > 1) prompts.value["don't"].splice(i, 1) }

function onNodeSelected(label) {
  selectedNodeLabel.value = label
  if (!selectedPromptNode.value) {
    prompts.value.var_prompt = prompts.value.var_prompt || []
    prompts.value.var_prompt.push({
      id: label,
      displayName: label,
      node_class: 'prompt',
      type: 'advanced',
      goal: '',
      tone: '',
      example: '',
      ext_info: 'disabled',
      need_answer: true,
      next: [],
    })
  }
}

const draftConfig = computed(() => ({ info: info.value, prompts: prompts.value, layout: layout.value }))

onMounted(async () => {
  await loadCharacter()
  navbarStore.setAction('save', save)
})

onBeforeUnmount(() => {
  navbarStore.clearAction()
})
</script>

<template>
  <div class="editor" v-if="!loading">
    <div class="editor-inner">
      <div class="tabs-bar">
        <button class="tab" :class="{ active: activeTab === 'base' }" @click="activeTab = 'base'">Base prompt</button>
        <button class="tab" :class="{ active: activeTab === 'graph' }" @click="activeTab = 'graph'">Graph</button>
      </div>

      <div v-if="saveError" class="save-error">{{ saveError }}</div>

      <!-- BASE PROMPT TAB -->
      <div v-if="activeTab === 'base'" class="tab-content base-tab">
        <div class="form-col scrollable">
          <section class="form-section">
            <div class="section-header">Basic Info</div>
            <div class="avatar-row">
              <label class="avatar-upload" title="Upload avatar">
                <img v-if="avatarPreview" :src="avatarPreview" alt="avatar" />
                <span v-else class="avatar-plus">+</span>
                <input type="file" accept="image/*" @change="onAvatarChange" hidden />
              </label>
              <div class="name-desc">
                <div class="field">
                  <label>Character name:</label>
                  <input v-model="info.name" type="text" />
                </div>
                <div class="field">
                  <label>Description</label>
                  <textarea v-model="info.description" rows="3" />
                </div>
              </div>
            </div>
          </section>

          <section class="form-section collapsible">
            <div class="section-header">Base instructions</div>
            <div class="field">
              <label>Character introduction:</label>
              <textarea v-model="prompts.base_prompt" rows="4" />
            </div>
            <div class="field">
              <label>Do's</label>
              <div class="list-field" v-for="(item, i) in prompts.do" :key="i">
                <input v-model="prompts.do[i]" type="text" />
                <button class="remove-btn" @click="removeDo(i)">×</button>
              </div>
              <button class="add-list-btn" @click="addDo">Add</button>
            </div>
            <div class="field">
              <label>Dont's</label>
              <div class="list-field" v-for="(item, i) in prompts[`don't`]" :key="i">
                <input v-model="prompts[`don't`][i]" type="text" />
                <button class="remove-btn" @click="removeDont(i)">×</button>
              </div>
              <button class="add-list-btn" @click="addDont">Add</button>
            </div>
          </section>

          <section class="form-section collapsible">
            <div class="section-header">Context</div>
            <div class="field">
              <label>Setting:</label>
              <textarea v-model="prompts.context.setting" rows="3" />
            </div>
            <div class="field">
              <label>Personality traits:</label>
              <textarea v-model="prompts.context.personality" rows="3" />
            </div>
            <div class="field">
              <label>Background information</label>
              <textarea v-model="prompts.context.background" rows="3" />
            </div>
            <div class="field">
              <label>Role:</label>
              <textarea v-model="prompts.context.role" rows="3" />
            </div>
          </section>

          <section class="form-section collapsible">
            <div class="section-header">Retrieval argumented generation:</div>
            <div class="field">
              <label>Scheme</label>
              <input v-model="info.rag.ragScheme" type="text" placeholder="e.g. hussite_wars" />
            </div>
            <div class="field">
              <label>Point of view</label>
              <input v-model="info.rag.pov" type="text" placeholder="e.g. jan_zizka" />
            </div>
          </section>
        </div>

        <div class="chat-col">
          <TestChatPanel :draft-config="draftConfig" />
        </div>
      </div>

      <!-- GRAPH TAB -->
      <div v-if="activeTab === 'graph'" class="tab-content graph-tab">
        <div class="node-editor-col scrollable">
          <div v-if="!selectedPromptNode" class="node-hint">
            Click a node to edit its properties.
          </div>
          <template v-else>
            <h3 class="node-title">{{ selectedPromptNode.displayName || selectedPromptNode.id }}</h3>
            <div class="field">
              <label>Instruction</label>
              <textarea v-model="selectedPromptNode.goal" rows="4" />
            </div>
            <div class="field">
              <label>tone</label>
              <input v-model="selectedPromptNode.tone" type="text" />
            </div>
            <div class="field">
              <label>example</label>
              <input v-model="selectedPromptNode.example" type="text" />
            </div>
            <div class="field">
              <label>information retrieval</label>
              <select v-model="selectedPromptNode.ext_info">
                <option value="disabled">disabled</option>
                <option value="enabled">enabled</option>
              </select>
            </div>
          </template>
        </div>

        <div class="graph-col">
          <GraphEditor
            :layout-data="layout"
            :var-prompt="prompts.var_prompt || []"
            @nodeSelected="onNodeSelected"
            @update:layoutData="layout = $event"
          />
        </div>

        <div class="chat-col">
          <TestChatPanel :draft-config="draftConfig" />
        </div>
      </div>
    </div>
  </div>

  <div v-else class="loading-screen">Loading character…</div>
</template>

<style scoped>
.editor {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.loading-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
}

.tabs-bar {
  display: flex;
  justify-content: center;
  gap: 0;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.tab {
  padding: 0.45rem 1.75rem;
  border: 1px solid var(--primary);
  background: white;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.tab:first-child { border-radius: var(--radius) 0 0 var(--radius); }
.tab:last-child { border-radius: 0 var(--radius) var(--radius) 0; }

.tab.active {
  background: var(--primary);
  color: white;
}

.save-error {
  background: #ffe4e4;
  color: #c0392b;
  font-size: 0.85rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #f5c6c6;
}

.tab-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* BASE PROMPT TAB */
.base-tab .form-col {
  flex: 1;
  min-width: 0;
}

.base-tab .chat-col {
  width: 320px;
  border-left: 1px solid var(--border);
  flex-shrink: 0;
}

/* GRAPH TAB */
.graph-tab .node-editor-col {
  width: 260px;
  border-right: 1px solid var(--border);
  flex-shrink: 0;
}

.graph-tab .graph-col {
  flex: 1;
  min-width: 0;
  position: relative;
}

.graph-tab .chat-col {
  width: 280px;
  border-left: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
}

.scrollable {
  overflow-y: auto;
  padding: 1rem 1.25rem;
}

/* FORM STYLES */
.form-section {
  margin-bottom: 0.5rem;
}

.section-header {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.6rem 0 0.4rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 0.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.avatar-row {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  margin-top: 0.5rem;
}

.avatar-upload {
  width: 72px;
  height: 72px;
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  overflow: hidden;
  transition: border-color 0.15s;
}

.avatar-upload:hover {
  border-color: var(--primary);
}

.avatar-upload img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-plus {
  font-size: 1.8rem;
  color: var(--text-muted);
  line-height: 1;
}

.name-desc {
  flex: 1;
  min-width: 0;
}

.field {
  margin-bottom: 0.75rem;
}

.field label {
  display: block;
  font-size: 0.82rem;
  font-weight: 500;
  margin-bottom: 0.3rem;
  color: var(--text);
}

.field input,
.field textarea,
.field select {
  width: 100%;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 0.88rem;
  resize: vertical;
  background: white;
}

.field input:focus,
.field textarea:focus,
.field select:focus {
  outline: none;
  border-color: var(--primary);
}

.list-field {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.4rem;
}

.list-field input {
  flex: 1;
}

.remove-btn {
  background: var(--primary);
  color: white;
  width: 26px;
  height: 26px;
  border-radius: 4px;
  font-size: 1.1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  align-self: center;
}

.add-list-btn {
  background: var(--primary);
  color: white;
  padding: 0.3rem 0.9rem;
  border-radius: var(--radius);
  font-size: 0.82rem;
  margin-top: 0.25rem;
  transition: background 0.15s;
}

.add-list-btn:hover {
  background: var(--primary-hover);
}

/* NODE EDITOR */
.node-hint {
  color: var(--text-muted);
  font-size: 0.85rem;
  text-align: center;
  margin-top: 2rem;
  padding: 0 0.5rem;
}

.node-title {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 1rem;
}
</style>
