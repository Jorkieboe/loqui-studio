<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { VueFlow, useVueFlow, Handle } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import '@vue-flow/core/dist/style.css'

const props = defineProps({
  layoutData: { type: Object, default: () => ({ nodes: [], connections: [] }) },
  varPrompt: { type: Array, default: () => [] },
})

const emit = defineEmits(['nodeSelected', 'update:layoutData'])

const { onNodeClick, fitView, addNodes, addEdges } = useVueFlow()

const nodes = ref([])
const edges = ref([])
const selectedNodeId = ref(null)

function buildGraph() {
  nodes.value = (props.layoutData.nodes || []).map(n => {
    const promptNode = props.varPrompt.find(p => p.id === n.label)
    return {
      id: n.id,
      position: n.position || { x: 0, y: 0 },
      label: promptNode?.displayName || n.label,
      type: n.type === 'start-node' ? 'start-node' : 'prompt-node',
      data: {
        label: promptNode?.displayName || n.label,
        goal: promptNode?.goal || '',
        nodeLabel: n.label,
        nodeClass: n.node_class,
        type: n.type,
      },
      class: n.type === 'start-node' ? 'start-node' : 'prompt-node',
    }
  })

  edges.value = (props.layoutData.connections || []).map(c => ({
    id: c.id,
    source: c.source,
    target: c.target,
    animated: false,
    style: { stroke: '#1a1a1a', strokeWidth: 2 },
  }))
}

onNodeClick(({ node }) => {
  selectedNodeId.value = node.id
  const layoutNode = props.layoutData.nodes.find(n => n.id === node.id)
  if (layoutNode) {
    emit('nodeSelected', layoutNode.label)
  }
})

function addNewNode() {
  const id = `node_${Date.now()}`
  const label = `node_${nodes.value.length}`
  const promptLabel = `node${nodes.value.length}`

  const newLayoutNode = {
    id,
    label: promptLabel,
    node_class: 'prompt',
    type: 'advanced',
    position: { x: 200, y: (nodes.value.length) * 160 + 80 },
    data: {},
  }

  const updatedLayout = {
    ...props.layoutData,
    nodes: [...(props.layoutData.nodes || []), newLayoutNode],
  }
  emit('update:layoutData', updatedLayout)
}

watch(() => [props.layoutData, props.varPrompt], buildGraph, { deep: true, immediate: true })

onMounted(() => {
  setTimeout(() => fitView(), 100)
})
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
      @nodes-change="$emit('nodesChange', $event)"
    >
      <Background pattern-color="#e0e0e0" gap="24" />

      <template #node-start-node="nodeProps">
        <div class="node start-node" :class="{ selected: selectedNodeId === nodeProps.id }">
          <Handle type="source" position="bottom" style="background: #3DCFAC" />
          <div class="node-label">{{ nodeProps.data.label }}</div>
        </div>
      </template>

      <template #node-prompt-node="nodeProps">
        <div class="node prompt-node" :class="{ selected: selectedNodeId === nodeProps.id }">
          <Handle type="target" position="top" style="background: #3DCFAC; width:10px; height:10px" />
          <div class="node-name">{{ nodeProps.data.label }}</div>
          <div v-if="nodeProps.data.goal" class="node-goal">{{ nodeProps.data.goal }}</div>
          <Handle type="source" position="bottom" style="background: #3DCFAC; width:10px; height:10px" />
        </div>
      </template>
    </VueFlow>

    <button class="add-node-btn" @click="addNewNode">+ Add node</button>
  </div>
</template>

<style scoped>
.graph-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  background: #fafafa;
}

.vue-flow-graph {
  width: 100%;
  height: 100%;
}

.node {
  background: white;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  min-width: 120px;
  max-width: 200px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12);
}

.node.selected {
  border-color: var(--primary);
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12), 0 0 0 3px rgba(61, 207, 172, 0.35);
}

.node.start-node {
  min-width: 80px;
  padding: 0.4rem 0.75rem;
  background: var(--primary-light);
  text-align: center;
}

.node.prompt-node {
  border-bottom: 3px solid var(--primary);
  padding: 0;
}

.node-label {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text);
}

.node-name {
  padding: 0.4rem 0.6rem;
  font-weight: 600;
  font-size: 0.85rem;
  border-bottom: 1px solid rgba(0,0,0,0.08);
  background: var(--primary-light);
  border-radius: calc(var(--radius) - 2px) calc(var(--radius) - 2px) 0 0;
}

.node-goal {
  padding: 0.35rem 0.6rem;
  font-size: 0.78rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

.add-node-btn {
  position: absolute;
  bottom: 1rem;
  left: 1rem;
  background: var(--primary);
  color: white;
  padding: 0.45rem 1rem;
  border-radius: var(--radius);
  font-size: 0.85rem;
  z-index: 10;
  transition: background 0.15s;
}

.add-node-btn:hover {
  background: var(--primary-hover);
}
</style>
