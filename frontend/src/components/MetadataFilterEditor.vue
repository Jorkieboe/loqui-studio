<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  fields:     { type: Array,  default: () => [] },
  ragScheme:  { type: String, default: '' },
  title:      { type: String, default: 'RAG metadata filter' },
  hint:       { type: String, default: 'Chunks not matching these expected values are removed before embedding search.' },
})

const emit = defineEmits(['update:modelValue'])

const mergedFields = computed(() => {
  const byKey = new Map()
  for (const field of props.fields || []) {
    if (field?.key) {
      byKey.set(field.key, { key: field.key, values: field.values || [] })
    }
  }
  for (const key of Object.keys(props.modelValue || {})) {
    if (!byKey.has(key)) {
      byKey.set(key, { key, values: [] })
    }
  }
  return Array.from(byKey.values())
})

function getSelectedList(key) {
  const val = props.modelValue?.[key]
  if (Array.isArray(val)) return val.map(v => String(v).trim()).filter(Boolean)
  if (typeof val === 'string') return val.split(',').map(v => v.trim()).filter(Boolean)
  return []
}

function getSelectedText(key) {
  return getSelectedList(key).join(', ')
}

function updateKey(key, values) {
  const next = { ...(props.modelValue || {}) }
  const cleaned = values.map(v => v.trim()).filter(Boolean)
  if (cleaned.length) {
    next[key] = cleaned
  } else {
    delete next[key]
  }
  emit('update:modelValue', next)
}

function isValueActive(key, val) {
  const target = String(val).trim().toLowerCase()
  return getSelectedList(key).some(v => v.toLowerCase() === target)
}

function toggleChip(key, val) {
  const current = getSelectedList(key)
  const target = String(val).trim().toLowerCase()
  const exists = current.some(v => v.toLowerCase() === target)
  const updated = exists
    ? current.filter(v => v.toLowerCase() !== target)
    : [...current, String(val).trim()]
  updateKey(key, updated)
}

function onInput(key, rawValue) {
  const parts = String(rawValue || '').split(',').map(v => v.trim()).filter(Boolean)
  updateKey(key, parts)
}
</script>

<template>
  <div class="meta-filter-box">
    <div class="meta-filter-title">{{ title }}</div>
    <p v-if="!ragScheme" class="meta-filter-empty">
      Set a RAG scheme in Base prompt to list metadata entries.
    </p>
    <p v-else-if="!mergedFields.length" class="meta-filter-empty">
      No metadata entries found for scheme "{{ ragScheme }}".
    </p>
    <div v-else class="meta-fields-list">
      <div v-for="field in mergedFields" :key="field.key" class="meta-field-item">
        <label class="meta-field-key">{{ field.key }}</label>
        <div v-if="field.values.length" class="meta-chips">
          <button
            v-for="val in field.values"
            :key="val"
            type="button"
            class="meta-chip"
            :class="{ active: isValueActive(field.key, val) }"
            @click="toggleChip(field.key, val)"
          >
            {{ val }}
          </button>
        </div>
        <input
          type="text"
          class="meta-input"
          :value="getSelectedText(field.key)"
          placeholder="Expected values (comma-separated, or leave empty)"
          @input="onInput(field.key, $event.target.value)"
        />
      </div>
    </div>
    <p v-if="ragScheme && mergedFields.length" class="meta-filter-hint">{{ hint }}</p>
  </div>
</template>

<style scoped>
.meta-filter-box {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}

.meta-filter-title {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.45rem;
}

.meta-filter-empty {
  font-size: 0.76rem;
  color: var(--text-muted);
  line-height: 1.45;
}

.meta-fields-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.meta-field-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.meta-field-key {
  font-size: 0.76rem;
  font-weight: 600;
  color: var(--text-muted);
  font-family: monospace;
}

.meta-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}

.meta-chip {
  font-size: 0.72rem;
  padding: 0.15rem 0.45rem;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: #f8fafc;
  color: var(--text);
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.meta-chip:hover {
  border-color: var(--primary);
}

.meta-chip.active {
  background: var(--primary);
  border-color: var(--primary-dark);
  color: white;
  font-weight: 600;
}

.meta-input {
  width: 100%;
  padding: 0.4rem 0.55rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 0.82rem;
  background: white;
}

.meta-input:focus {
  outline: none;
  border-color: var(--primary);
}

.meta-filter-hint {
  font-size: 0.74rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
  line-height: 1.45;
}
</style>