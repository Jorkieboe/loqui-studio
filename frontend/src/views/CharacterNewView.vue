<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const templateName = ref('')
const description = ref('')
const error = ref('')
const loading = ref(false)

function slugify(name) {
  return name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '').slice(0, 40) || 'character'
}

async function createManual() {
  if (!templateName.value.trim()) {
    error.value = 'Template name is required.'
    return
  }

  const id = slugify(templateName.value)
  loading.value = true
  error.value = ''

  try {
    const payload = {
      info: {
        id,
        name: templateName.value.trim(),
        description: description.value.trim(),
        tags: [],
        language: 'en',
        color: '#3DCFAC',
        idle_timeout_seconds: 300,
        rag: { ragScheme: '', pov: '', chunksize: 4 },
      },
      prompts: {
        base_prompt: '',
        do: [''],
        "don't": [''],
        context: { setting: '', personality: '', background: '', role: '' },
        var_prompt: [
          {
            id: 'start',
            displayName: 'Start',
            node_class: 'flow',
            type: 'start-node',
            next: [{ target: 'welcome' }],
          },
          {
            id: 'welcome',
            displayName: 'Welcome',
            node_class: 'prompt',
            type: 'advanced',
            goal: '',
            tone: '',
            example: '',
            ext_info: 'disabled',
            need_answer: true,
            next: [],
          },
        ],
      },
      layout: {
        nodes: [
          { id: 'node_start_idx', label: 'start', node_class: 'flow', type: 'start-node', position: { x: 200, y: 80 }, data: {} },
          { id: 'node_welcome_idx', label: 'welcome', node_class: 'prompt', type: 'advanced', position: { x: 200, y: 240 }, data: {} },
        ],
        connections: [
          { id: 'conn_01', source: 'node_start_idx', sourceOutput: 'out', target: 'node_welcome_idx', targetInput: 'in', data: { label: '' } },
        ],
      },
    }

    const res = await fetch(`/api/characters/item/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail || 'Failed to create character')
    }

    router.push(`/characters/${id}/edit`)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function createAI() {
  alert('AI generation is not yet implemented. Use Manual to set up the character yourself.')
}
</script>

<template>
  <div class="new-character">
    <div class="form-card">
      <h1>Create a character</h1>

      <div class="field">
        <label>Template name: <span class="required">required</span></label>
        <input v-model="templateName" type="text" placeholder="" />
      </div>

      <div class="field">
        <label>Describe your character</label>
        <textarea v-model="description" rows="5" />
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <div class="actions">
        <button class="btn-primary" :disabled="loading" @click="createManual">
          {{ loading ? 'Creating...' : 'Manual' }}
        </button>
        <button class="btn-secondary" @click="createAI">Create AI</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.new-character {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  padding: 2rem;
  height: 100%;
  overflow-y: auto;
}

.form-card {
  width: 100%;
  max-width: 560px;
}

h1 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 2rem;
}

.field {
  margin-bottom: 1.5rem;
}

label {
  display: block;
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.required {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--text-muted);
}

input, textarea {
  width: 100%;
  padding: 0.6rem 0.75rem;
  border: 1px solid #aaa;
  border-radius: var(--radius);
  font-size: 0.95rem;
  resize: vertical;
  background: white;
}

input:focus, textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.error {
  color: #e53e3e;
  font-size: 0.87rem;
  margin-bottom: 1rem;
}

.actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

.btn-primary {
  background: var(--primary);
  color: white;
  padding: 0.65rem 1.75rem;
  border-radius: var(--radius);
  font-size: 0.95rem;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--primary-light);
  color: var(--text);
  padding: 0.65rem 1.75rem;
  border-radius: var(--radius);
  font-size: 0.95rem;
  font-weight: 500;
  transition: background 0.15s;
}

.btn-secondary:hover {
  background: #b0ddd1;
}
</style>
