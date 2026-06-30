<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { VueFlow, useVueFlow, Handle } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import '@vue-flow/core/dist/style.css'

const props = defineProps({
  layoutData: { type: Object, default: () => ({ nodes: [], connections: [] }) },
  varPrompt:  { type: Array,  default: () => [] },
})

const emit = defineEmits(['nodeSelected', 'addNode'])

const { onNodeClick, fitView } = useVueFlow()

const nodes        = ref([])
const edges        = ref([])
const selectedId   = ref(null)
const showAddMenu  = ref(false)

const hasDeflect = computed(() => props.varPrompt.some(n => n.type === 'deflect'))
const hasSilence = computed(() => props.varPrompt.some(n => n.type === 'silence'))

const FLOW_TYPES = new Set(['start-node', 'end-node', 'loop-node', 'cycle-node'])

function getVueFlowType(n) {
  if (FLOW_TYPES.has(n.type)) return n.type          // 'start-node', 'end-node', etc.
  if (n.type === 'deflect')   return 'deflect-node'
  if (n.type === 'silence')   return 'silence-node'
  return 'prompt-node'                                // basic / advanced
}

function buildGraph() {
  // Nodes come from varPrompt; positions from layoutData
  nodes.value = props.varPrompt.map(n => {
    const layoutNode = props.layoutData.nodes?.find(l => l.label === n.id || l.id === n.id)
    return {
      id:       n.id,
      position: layoutNode?.position || { x: 0, y: 0 },
      type:     getVueFlowType(n),
      data: {
        label:     n.displayName || n.id,
        goal:      n.goal      || '',
        loopCount: n.loop_count ?? 3,
      },
    }
  })

  // Edges come from varPrompt[].next
  const allEdges = []
  for (const n of props.varPrompt) {
    const isLoop = n.type === 'loop-node'
    ;(n.next || []).forEach((conn, i) => {
      if (!conn.target) return
      allEdges.push({
        id:           `e_${n.id}__${conn.target}__${i}`,
        source:       n.id,
        target:       conn.target,
        sourceHandle: isLoop ? (i === 0 ? 'loop-body' : 'loop-exit') : null,
        animated:     false,
        style:        { stroke: '#1a1a1a', strokeWidth: 2 },
      })
    })
  }
  edges.value = allEdges
}

onNodeClick(({ node }) => {
  selectedId.value = node.id
  emit('nodeSelected', node.id)
})

function addNode(type) {
  emit('addNode', type)
  showAddMenu.value = false
}

watch(() => [props.varPrompt, props.layoutData], buildGraph, { deep: true, immediate: true })
onMounted(() => setTimeout(() => fitView(), 100))
</script>

<template>
  <div class="graph-wrapper">
    <VueFlow
      v-model:nodes="nodes"
      v-model:edges="edges"
      :default-zoom="1"
      :min-zoom="0.3"
      :max-zoom="2"
      fit-view-on-init
      class="vue-flow-graph"
    >
      <Background pattern-color="#e0e0e0" gap="24" />

      <!-- START -->
      <template #node-start-node="{ id, data }">
        <div class="node node-flow node-start" :class="{ selected: selectedId === id }">
          <div class="flow-label">{{ data.label }}</div>
          <Handle type="source" position="bottom" class="handle" />
        </div>
      </template>

      <!-- END -->
      <template #node-end-node="{ id, data }">
        <div class="node node-flow node-end" :class="{ selected: selectedId === id }">
          <Handle type="target" position="top" class="handle" />
          <div class="flow-label">{{ data.label }}</div>
        </div>
      </template>

      <!-- CYCLE -->
      <template #node-cycle-node="{ id, data }">
        <div class="node node-flow node-cycle" :class="{ selected: selectedId === id }">
          <Handle type="target" position="top" class="handle" />
          <div class="flow-label">{{ data.label }}</div>
          <Handle type="source" position="bottom" class="handle" />
        </div>
      </template>

      <!-- LOOP -->
      <template #node-loop-node="{ id, data }">
        <div class="node node-loop" :class="{ selected: selectedId === id }">
          <Handle type="target" position="top" class="handle" />
          <div class="loop-header">
            <span class="loop-name">{{ data.label }}</span>
            <span class="loop-count">×{{ data.loopCount }}</span>
          </div>
          <!-- Label row — flex so any number of outputs fit -->
          <div class="loop-outputs">
            <span class="loop-output-label">Body</span>
            <span class="loop-output-label">Exit</span>
          </div>
          <!-- Handles spread along the bottom edge using left % -->
          <Handle id="loop-body" type="source" position="bottom" :style="{ left: '25%' }" class="handle" />
          <Handle id="loop-exit" type="source" position="bottom" :style="{ left: '75%' }" class="handle" />
        </div>
      </template>

      <!-- PROMPT (basic / advanced) -->
      <template #node-prompt-node="{ id, data }">
        <div class="node node-content node-prompt" :class="{ selected: selectedId === id }">
          <Handle type="target" position="top" class="handle" />
          <div class="content-header prompt-header">{{ data.label }}</div>
          <div v-if="data.goal" class="content-goal">{{ data.goal }}</div>
          <Handle type="source" position="bottom" class="handle" />
        </div>
      </template>

      <!-- DEFLECT -->
      <template #node-deflect-node="{ id, data }">
        <div class="node node-content node-deflect" :class="{ selected: selectedId === id }">
          <Handle type="target" position="top" class="handle" />
          <div class="content-header deflect-header">{{ data.label }}</div>
          <div v-if="data.goal" class="content-goal">{{ data.goal }}</div>
          <Handle type="source" position="bottom" class="handle" />
        </div>
      </template>

      <!-- SILENCE -->
      <template #node-silence-node="{ id, data }">
        <div class="node node-content node-silence" :class="{ selected: selectedId === id }">
          <Handle type="target" position="top" class="handle" />
          <div class="content-header silence-header">{{ data.label }}</div>
          <div v-if="data.goal" class="content-goal">{{ data.goal }}</div>
          <Handle type="source" position="bottom" class="handle" />
        </div>
      </template>
    </VueFlow>

    <!-- Add node -->
    <div class="add-area">
      <button class="add-btn" @click.stop="showAddMenu = !showAddMenu">+ Add node</button>
      <div v-if="showAddMenu" class="add-menu">
        <p class="menu-label">Content</p>
        <button @click="addNode('basic')">Prompt (basic)</button>
        <button @click="addNode('advanced')">Prompt (advanced)</button>
        <button @click="addNode('deflect')" :disabled="hasDeflect" :title="hasDeflect ? 'Only one deflect allowed' : ''">
          Deflect{{ hasDeflect ? ' (exists)' : '' }}
        </button>
        <button @click="addNode('silence')" :disabled="hasSilence" :title="hasSilence ? 'Only one silence allowed' : ''">
          Silence{{ hasSilence ? ' (exists)' : '' }}
        </button>
        <hr class="menu-divider" />
        <p class="menu-label">Flow</p>
        <button @click="addNode('end-node')">End</button>
        <button @click="addNode('loop-node')">Loop</button>
        <button @click="addNode('cycle-node')">Cycle</button>
      </div>
    </div>
    <div v-if="showAddMenu" class="menu-backdrop" @click="showAddMenu = false" />
  </div>
</template>

<style scoped>
.graph-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  background: #fafafa;
}
.vue-flow-graph { width: 100%; height: 100%; }

/* Base */
.node {
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,.10);
  transition: box-shadow 0.15s;
}
.node.selected {
  box-shadow: 0 2px 8px rgba(0,0,0,.10), 0 0 0 3px rgba(61,207,172,.4);
}
.handle {
  width: 10px; height: 10px;
  background: #3DCFAC;
  border: 2px solid white;
}

/* ── Flow pills ── */
.node.node-flow {
  min-width: 76px;
  padding: 0.35rem 1rem;
  border-radius: 20px;
  text-align: center;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.node.node-start  { background: #3DCFAC; color: #fff; border: 2px solid #2cb893; }
.node.node-end    { background: #1e293b; color: #fff; border: 2px solid #0f172a; }
.node.node-cycle  { background: #F97316; color: #fff; border: 2px solid #ea6c0a; }
.flow-label { pointer-events: none; }

/* ── Loop ── */
.node.node-loop {
  min-width: 120px;
  background: white;
  border: 2px solid #6366F1;
  border-radius: 8px;
  position: relative;
}
.node.node-loop.selected { border-color: #4F46E5; }
.loop-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.4rem 0.65rem;
  background: #EEF2FF;
  border-radius: 6px 6px 0 0;
}
.loop-name  { font-weight: 700; font-size: 0.82rem; color: #4F46E5; }
.loop-count {
  font-size: 0.75rem; font-weight: 700; color: #6366F1;
  background: white; border: 1px solid #C7D2FE;
  border-radius: 4px; padding: 0.05rem 0.3rem;
}
/* Flex row of output labels — one per handle, scales to any count */
.loop-outputs {
  display: flex;
  justify-content: space-around;
  padding: 0.25rem 0.5rem 0.55rem;
}
.loop-output-label {
  font-size: 0.62rem;
  font-weight: 700;
  color: #6366F1;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  pointer-events: none;
}

/* ── Content nodes ── */
.node.node-content {
  min-width: 140px;
  max-width: 210px;
  background: white;
  border: 2px solid var(--border);
  border-radius: var(--radius);
}
.content-header {
  padding: 0.4rem 0.65rem;
  font-weight: 700;
  font-size: 0.82rem;
  border-radius: calc(var(--radius) - 2px) calc(var(--radius) - 2px) 0 0;
}
.prompt-header  { background: #E6FAF5; color: #1a6b55; border-bottom: 1px solid #c0ede2; }
.deflect-header { background: #FEF3C7; color: #92400E; border-bottom: 1px solid #FDE68A; }
.silence-header { background: #F1F5F9; color: #475569; border-bottom: 1px solid #CBD5E1; }

.node.node-prompt  { border-bottom: 3px solid #3DCFAC; }
.node.node-deflect { border-bottom: 3px solid #F59E0B; }
.node.node-silence { border-bottom: 3px solid #64748B; }

.content-goal {
  padding: 0.3rem 0.65rem;
  font-size: 0.74rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 206px;
}

/* ── Add area ── */
.add-area {
  position: absolute;
  bottom: 1rem; left: 1rem;
  z-index: 10;
}
.add-btn {
  background: var(--primary);
  color: white;
  padding: 0.45rem 1rem;
  border-radius: var(--radius);
  font-size: 0.85rem;
  transition: background .15s;
}
.add-btn:hover { background: var(--primary-hover); }

.add-menu {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 4px 16px rgba(0,0,0,.12);
  padding: 0.3rem 0;
  min-width: 160px;
  z-index: 11;
}
.menu-label {
  font-size: 0.68rem; font-weight: 700;
  letter-spacing: .05em; text-transform: uppercase;
  color: var(--text-muted);
  padding: 0.3rem 0.75rem 0.1rem;
  margin: 0;
}
.add-menu button {
  display: block; width: 100%;
  text-align: left;
  padding: 0.35rem 0.75rem;
  font-size: 0.85rem;
  color: var(--text);
  background: none;
  transition: background .1s;
}
.add-menu button:hover:not(:disabled) { background: var(--primary-light); }
.add-menu button:disabled { color: var(--text-muted); cursor: not-allowed; }
.menu-divider { border: none; border-top: 1px solid var(--border); margin: 0.3rem 0; }

.menu-backdrop {
  position: absolute;
  inset: 0;
  z-index: 9;
}
</style>
