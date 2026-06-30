const KEY = 'loqui_chat_sessions'

export function getSessions() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function saveSession(session) {
  const sessions = getSessions().filter(s => s.id !== session.id)
  sessions.unshift(session)
  localStorage.setItem(KEY, JSON.stringify(sessions.slice(0, 100)))
}

export function getSession(id) {
  return getSessions().find(s => s.id === id) || null
}

export function deleteSession(id) {
  const sessions = getSessions().filter(s => s.id !== id)
  localStorage.setItem(KEY, JSON.stringify(sessions))
}

export function createSessionId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7)
}
