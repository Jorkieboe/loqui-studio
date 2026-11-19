<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TestChatPanel from '../components/TestChatPanel.vue'
import GraphEditor from '../components/GraphEditor.vue'
import ValidationBlock from '../components/ValidationBlock.vue'
import { useNavbarStore } from '../stores/navbar'

const route = useRoute()
const router = useRouter()
const navbarStore = useNavbarStore()

const charId = computed(() => route.params.id)
const activeTab = ref('base')

const chatMessages     = ref([])
const chatSessionState = ref({ active_node_id: null, history: [] })

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

const selectedNodeId = ref(null)

const selectedNode = computed(() => {
  if (!selectedNodeId.value) return null
  return prompts.value.var_prompt?.find(n => n.id === selectedNodeId.value) || null
})

const isFlowNode     = computed(() => selectedNode.value?.node_class === 'flow')
const isPromptNode   = computed(() => selectedNode.value?.node_class === 'prompt')
const isReactiveNode = computed(() => selectedNode.value?.node_class === 'reactive')
const isBridgeNode   = computed(() => selectedNode.value?.type === 'bridge-node')

const editingNodeTitle = ref(false)
const nodeTitleInput = ref(null)

async function startEditTitle() {
  editingNodeTitle.value = true
  await nextTick()
  nodeTitleInput.value?.focus()
  nodeTitleInput.value?.select()
}

watch(selectedNodeId, () => { editingNodeTitle.value = false })

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

function onNodeSelected(id) {
  selectedNodeId.value = id
}

const FLOW_TYPES = new Set(['start-node', 'end-node', 'loop-node', 'cycle-node', 'bridge-node'])

const NODE_DEFAULTS = {
  'basic':               { node_class: 'prompt', displayName: 'New node', goal: '', tone: '', next: [] },
  'advanced':            { node_class: 'prompt', displayName: 'New node', goal: '', tone: '', example: '', follow_up: '', ext_info: 'disabled', next: [] },
  'deflect':             { node_class: 'prompt', displayName: 'Deflect',  goal: '', tone: '', example: '', next: [] },
  'silence':             { node_class: 'prompt', displayName: 'Silence',  goal: '', tone: '', example: '', next: [] },
  'start-node':          { node_class: 'flow',   displayName: 'Start',   next: [] },
  'end-node':            { node_class: 'flow',   displayName: 'End',     next: [] },
  'bridge-node':         { node_class: 'flow',   type: 'bridge-node', displayName: 'Bridge', goal: '', ext_info: 'reuse', next: [] },
  'loop-node':           { node_class: 'flow',   displayName: 'Loop',    loop_count: 3, next: [] },
  'cycle-node':          { node_class: 'flow',   displayName: 'Cycle',   next: [] },
  'reactive-flow':       { node_class: 'reactive', mode: 'flow', displayName: 'Reactive Flow', trigger_intent: '', flow_label: '', next: [] },
  'reactive-standalone': { node_class: 'reactive', mode: 'standalone', displayName: 'Reactive Standalone', trigger_intent: '', goal: '', tone: '', next: [] },
}

function resetChat() {
  chatMessages.value     = []
  chatSessionState.value = { active_node_id: null, history: [] }
}

function onConnectEdge({ source, target, sourceHandle }) {
  const node = prompts.value.var_prompt?.find(n => n.id === source)
  if (!node) return
  node.next = node.next || []

  if (node.type === 'loop-node') {
    const idx = sourceHandle === 'loop-body' ? 0 : 1
    node.next[idx] = { target }
  } else {
    if (!node.next.find(c => c.target === target))
      node.next.push({ target })
  }
  layout.value.connections = [
    ...(layout.value.connections || []).filter(c => !(c.source === source && c.target === target)),
    {
      id: `conn_${source}__${target}`,
      source,
      sourceOutput: sourceHandle || 'out',
      target,
      targetInput: 'in',
      data: { label: '' },
    },
  ]
  resetChat()
}

function onDisconnectEdges(connections) {
  for (const { source, target, sourceHandle } of connections) {
    const node = prompts.value.var_prompt?.find(n => n.id === source)
    if (node) {
      if (node.type === 'loop-node') {
        const idx = sourceHandle === 'loop-body' ? 0 : 1
        if (node.next?.[idx]?.target === target) node.next.splice(idx, 1)
      } else {
        node.next = (node.next || []).filter(c => c.target !== target)
      }
    }
    layout.value.connections = (layout.value.connections || []).filter(
      c => !(c.source === source && c.target === target)
    )
  }
  resetChat()
}

function onRemoveNodes(ids) {
  const idSet = new Set(ids)
  prompts.value.var_prompt = (prompts.value.var_prompt || []).filter(n => !idSet.has(n.id))
  layout.value.nodes      = (layout.value.nodes || []).filter(n => !idSet.has(n.id) && !idSet.has(n.label))
  for (const node of (prompts.value.var_prompt || []))
    node.next = (node.next || []).filter(c => !idSet.has(c.target))
  if (selectedNodeId.value && idSet.has(selectedNodeId.value))
    selectedNodeId.value = null
  resetChat()
}

function onUpdatePositions(updates) {
  for (const { id, position } of updates) {
    const existing = layout.value.nodes?.find(n => n.id === id || n.label === id)
    if (existing) {
      existing.position = position
    } else {
      layout.value.nodes = [...(layout.value.nodes || []), { id, label: id, position, data: {} }]
    }
  }
}

function onAddNode(type) {
  const defaults = NODE_DEFAULTS[type]
  if (!defaults) return

  const timestamp = Date.now()
  const count = prompts.value.var_prompt?.length || 0

  if (type === 'reactive-flow') {
    const reactiveId = `reactive_${timestamp}`
    const bridgeId = `bridge_${timestamp}`

    const reactiveNode = {
      id: reactiveId,
      type: 'reactive-node',
      ...defaults,
      next: [{ target: bridgeId }],
    }

    const bridgeDefaults = NODE_DEFAULTS['bridge-node']
    const bridgeNode = {
      id: bridgeId,
      ...bridgeDefaults,
      next: [],
    }

    prompts.value.var_prompt = [
      ...(prompts.value.var_prompt || []),
      reactiveNode,
      bridgeNode,
    ]

    layout.value.nodes = [
      ...(layout.value.nodes || []),
      {
        id: reactiveId,
        label: reactiveId,
        node_class: 'reactive',
        type: 'reactive-node',
        position: { x: 250, y: count * 160 },
        data: {},
      },
      {
        id: bridgeId,
        label: bridgeId,
        node_class: 'flow',
        type: 'bridge-node',
        position: { x: 250, y: (count + 1) * 160 },
        data: {},
      },
    ]

    layout.value.connections = [
      ...(layout.value.connections || []),
      {
        id: `conn_${reactiveId}__${bridgeId}`,
        source: reactiveId,
        sourceOutput: 'out',
        target: bridgeId,
        targetInput: 'in',
        data: { label: '' },
      },
    ]

    selectedNodeId.value = reactiveId
    return
  }

  const id = `${type}_${timestamp}`
  prompts.value.var_prompt = [...(prompts.value.var_prompt || []), { id, type, ...defaults }]
  layout.value.nodes = [...(layout.value.nodes || []), {
    id, label: id,
    node_class: defaults.node_class,
    type,
    position: { x: 250, y: count * 160 },
    data: {},
  }]
  selectedNodeId.value = id
}

const draftConfig = computed(() => ({ info: info.value, prompts: prompts.value, layout: layout.value }))

const validationErrors = computed(() => {
  const errors = []
  const p = prompts.value

  if (!p.base_prompt?.trim())
    errors.push('Character introduction is empty')

  const filledDos = (p.do || []).filter(v => v?.trim())
  if (filledDos.length < 3)
    errors.push(`At least 3 Do's required (${filledDos.length} filled)`)

  const filledDonts = (p["don't"] || []).filter(v => v?.trim())
  if (filledDonts.length < 3)
    errors.push(`At least 3 Don'ts required (${filledDonts.length} filled)`)

  const varPrompt = p.var_prompt || []
  const startNode = varPrompt.find(n => n.type === 'start-node')
  if (!startNode) {
    errors.push('Graph is missing a Start node')
  } else {
    const connected = (startNode.next || []).some(conn =>
      varPrompt.find(n => n.id === conn.target)?.node_class === 'prompt'
    )
    if (!connected) {
      errors.push('Start node must connect to at least one prompt node')
    }
  }

  const nodeMap = new Map((varPrompt || []).map(n => [n.id, n]))
  const reactiveFlows = (varPrompt || []).filter(n => n.node_class === 'reactive' && n.mode === 'flow')

  for (const rNode of reactiveFlows) {
    const visited = new Set()
    const queue = [rNode.id]
    let reachedBridge = false

    while (queue.length > 0) {
      const currId = queue.shift()
      if (visited.has(currId)) continue
      visited.add(currId)

      const currNode = nodeMap.get(currId)
      if (!currNode) continue

      if (currNode.type === 'bridge-node' || (currNode.node_class === 'flow' && currNode.type === 'bridge-node')) {
        reachedBridge = true
        break
      }

      for (const item of (currNode.next || [])) {
        const target = item?.target || item
        if (target && !visited.has(target)) {
          queue.push(target)
        }
      }
    }

    if (!reachedBridge) {
      errors.push(`Reactive flow '${rNode.displayName || rNode.id}' must end with a connected Bridge node.`)
    }
  }

  return errors
})

const isValid = computed(() => validationErrors.value.length === 0)

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
        <div class="tabs-track">
          <button class="tab" :class="{ active: activeTab === 'base' }" @click="activeTab = 'base'">Base prompt</button>
          <button class="tab" :class="{ active: activeTab === 'graph' }" @click="activeTab = 'graph'">Graph</button>
        </div>
      </div>

      <div v-if="saveError" class="save-error">{{ saveError }}</div>

      <!-- BASE PROMPT TAB -->
      <div v-if="activeTab === 'base'" class="tab-content base-tab">
        <div class="form-col scrollable">
          <div class="form-inner">
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
                  <textarea v-model="info.description" rows="4" />
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
              <input v-model="info.rag.pov" type="text" list="pov-options" placeholder="e.g. jan_zizka or None" />
              <datalist id="pov-options">
                <option value="None">None (skip POV filtering)</option>
              </datalist>
            </div>
          </section>
          </div>
        </div>

        <div class="chat-col">
          <ValidationBlock v-if="!isValid" :errors="validationErrors" />
          <TestChatPanel v-else :draft-config="draftConfig" v-model:messages="chatMessages" v-model:session-state="chatSessionState" />
        </div>
      </div>

      <!-- GRAPH TAB -->
      <div v-if="activeTab === 'graph'" class="tab-content graph-tab">
        <div class="node-editor-col scrollable">

          <div v-if="!selectedNode" class="node-hint">Click a node to edit its properties.</div>

          <!-- Bridge node -->
          <template v-else-if="isBridgeNode">
            <div class="node-title-row">
              <h3 v-if="!editingNodeTitle" class="node-title">{{ selectedNode.displayName }}</h3>
              <input
                v-else
                ref="nodeTitleInput"
                class="node-title-input"
                v-model="selectedNode.displayName"
                @blur="editingNodeTitle = false"
                @keydown.enter="editingNodeTitle = false"
                @keydown.escape="editingNodeTitle = false"
              />
              <button class="node-title-edit-btn" @click="startEditTitle" title="Rename node">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            </div>
            <div class="field">
              <label>Custom wrap-up directive (optional)</label>
              <textarea v-model="selectedNode.goal" rows="4" placeholder="Leave blank to use default bridge wrap-up instruction." />
            </div>
            <div class="field">
              <label>Information retrieval</label>
              <select v-model="selectedNode.ext_info">
                <option value="reuse">Reuse last info (default)</option>
                <option value="fetch">Fetch fresh info</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>
            <p class="field-hint">Wraps up the sub-flow, reuses external context by default, and prompts the user to return to shelved open topics.</p>
          </template>

          <!-- Flow: start / end / cycle -->
          <template v-else-if="isFlowNode && selectedNode.type !== 'loop-node' && !isBridgeNode">
            <div class="node-title-row">
              <h3 class="node-title">{{ selectedNode.displayName }}</h3>
            </div>
            <div class="node-hint" style="margin-top:1rem">No editable properties for this node.</div>
          </template>

          <!-- Flow: loop -->
          <template v-else-if="selectedNode.type === 'loop-node'">
            <div class="node-title-row">
              <h3 class="node-title">{{ selectedNode.displayName }}</h3>
            </div>
            <div class="field">
              <label>Loop count</label>
              <input type="number" min="1" v-model.number="selectedNode.loop_count" />
            </div>
            <p class="field-hint">Number of times the loop runs before exiting via the Exit handle.</p>
          </template>

          <!-- Reactive nodes: flow / standalone -->
          <template v-else-if="isReactiveNode">
            <div class="node-title-row">
              <h3 v-if="!editingNodeTitle" class="node-title">{{ selectedNode.displayName }}</h3>
              <input
                v-else
                ref="nodeTitleInput"
                class="node-title-input"
                v-model="selectedNode.displayName"
                @blur="editingNodeTitle = false"
                @keydown.enter="editingNodeTitle = false"
                @keydown.escape="editingNodeTitle = false"
              />
              <button class="node-title-edit-btn" @click="startEditTitle" title="Rename node">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            </div>

            <div class="field">
              <label>Mode</label>
              <select v-model="selectedNode.mode">
                <option value="flow">Flow</option>
                <option value="standalone">Standalone</option>
              </select>
            </div>

            <div class="field">
              <label>Trigger intent</label>
              <textarea v-model="selectedNode.trigger_intent" rows="3" placeholder="Condition or user intent triggering this node..." />
            </div>
            <p class="field-hint">Used by the model to route to this node when the user brings up this topic.</p>

            <div class="field" v-if="selectedNode.mode === 'flow'">
              <label>Flow label</label>
              <input v-model="selectedNode.flow_label" type="text" placeholder="e.g. dinner & restaurants" />
            </div>
            <p class="field-hint" v-if="selectedNode.mode === 'flow'">Human-readable topic title used when offering to resume this shelved topic.</p>

            <!-- Instructions only shown for standalone reactive nodes -->
            <template v-if="selectedNode.mode === 'standalone'">
              <div class="field">
                <label>Instruction</label>
                <textarea v-model="selectedNode.goal" rows="4" />
              </div>

              <div class="field">
                <label>Tone</label>
                <input v-model="selectedNode.tone" type="text" />
              </div>
            </template>
          </template>

          <!-- Prompt nodes: basic / advanced / deflect / silence -->
          <template v-else-if="isPromptNode">
            <div class="node-title-row">
              <h3 v-if="!editingNodeTitle" class="node-title">{{ selectedNode.displayName }}</h3>
              <input
                v-else
                ref="nodeTitleInput"
                class="node-title-input"
                v-model="selectedNode.displayName"
                @blur="editingNodeTitle = false"
                @keydown.enter="editingNodeTitle = false"
                @keydown.escape="editingNodeTitle = false"
              />
              <button class="node-title-edit-btn" @click="startEditTitle" title="Rename node">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            </div>

            <div class="field">
              <label>Instruction</label>
              <textarea v-model="selectedNode.goal" rows="4" />
            </div>

            <div class="field">
              <label>Tone</label>
              <input v-model="selectedNode.tone" type="text" />
            </div>

            <div v-if="selectedNode.type !== 'basic'" class="field">
              <label>Example</label>
              <textarea v-model="selectedNode.example" rows="2" />
            </div>

            <template v-if="selectedNode.type === 'advanced'">
              <div class="field">
                <label>Follow up</label>
                <input v-model="selectedNode.follow_up" type="text" />
              </div>
              <div class="field">
                <label>Information retrieval</label>
                <select v-model="selectedNode.ext_info">
                  <option value="disabled">Disabled</option>
                  <option value="fetch">Fetch</option>
                  <option value="reuse">Reuse</option>
                </select>
              </div>
            </template>
          </template>
        </div>

        <div class="graph-col">
          <GraphEditor
            :layout-data="layout"
            :var-prompt="prompts.var_prompt || []"
            :active-node-id="chatSessionState.active_node_id"
            @nodeSelected="onNodeSelected"
            @addNode="onAddNode"
            @connectEdge="onConnectEdge"
            @disconnectEdges="onDisconnectEdges"
            @removeNodes="onRemoveNodes"
            @updatePositions="onUpdatePositions"
          />
        </div>

        <div class="chat-col">
          <ValidationBlock v-if="!isValid" :errors="validationErrors" />
          <TestChatPanel v-else :draft-config="draftConfig" v-model:messages="chatMessages" v-model:session-state="chatSessionState" />
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
  align-items: center;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.tabs-track {
  display: flex;
  width: 380px;
  background: var(--primary);
  border-radius: 6px;
  padding: 4px;
  gap: 0;
}

.tab {
  flex: 1;
  padding: 0.45rem 0;
  text-align: center;
  background: transparent;
  color: white;
  font-size: 0.92rem;
  font-weight: 400;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, font-weight 0.1s;
}

.tab.active {
  background: white;
  color: #2a2a2a;
  font-weight: 600;
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

.base-tab .form-col {
  flex: 1;
  min-width: 0;
}

.base-tab .chat-col {
  width: 320px;
  border-left: 1px solid var(--border);
  flex-shrink: 0;
}

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
  gap: 1.5rem;
  align-items: center;
  margin-top: 0.75rem;
}

.avatar-upload {
  width: 140px;
  height: 140px;
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
  font-size: 3.5rem;
  color: var(--text-muted);
  line-height: 1;
}

.name-desc {
  flex: 1;
  min-width: 0;
}

.field {
  margin-bottom: 0.75rem;
  max-width: 1000px;
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

.node-hint {
  color: var(--text-muted);
  font-size: 0.85rem;
  text-align: center;
  margin-top: 2rem;
  padding: 0 0.5rem;
}

.field-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: -0.25rem 0 0.75rem;
  line-height: 1.5;
}

.node-title-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 1rem;
}

.node-title {
  flex: 1;
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-title-input {
  flex: 1;
  font-size: 1rem;
  font-weight: 700;
  border: 1px solid var(--primary);
  border-radius: 4px;
  padding: 0.15rem 0.35rem;
  outline: none;
  background: white;
}

.node-title-edit-btn {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  background: none;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.node-title-edit-btn:hover {
  background: var(--primary-light);
  color: var(--primary-dark);
}
</style>