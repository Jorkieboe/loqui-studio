const API = '/api/conversations'

export async function getSessions() {
  try {
    const res = await fetch(API)
    return res.ok ? res.json() : []
  } catch { return [] }
}

export async function createSession(characterId, characterName, characterAvatar) {
  const res = await fetch(API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ character_id: characterId, character_name: characterName, character_avatar: characterAvatar || null }),
  })
  if (!res.ok) {
    throw new Error(`Failed to create session (${res.status})`)
  }
  return res.json()
}

export async function getSession(id) {
  try {
    const res = await fetch(`${API}/${id}`)
    return res.ok ? res.json() : null
  } catch { return null }
}

export async function deleteSession(id) {
  const res = await fetch(`${API}/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    throw new Error(`Failed to delete session (${res.status})`)
  }
}

export async function appendMessage(conversationId, role, content) {
  try {
    const res = await fetch(`${API}/${conversationId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, content }),
    })
    return res.ok ? res.json() : null
  } catch { return null }
}

export async function updateNode(conversationId, nodeId) {
  try {
    await fetch(`${API}/${conversationId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_node_id: nodeId }),
    })
  } catch { /* non-critical */ }
}