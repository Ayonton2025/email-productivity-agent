let nextId = 0
let snapshot = []
const listeners = new Set()
const emit = () => listeners.forEach((listener) => listener())
export const notifications = {
  subscribe(listener) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getSnapshot() {
    return snapshot
  },
  dismiss(id) {
    snapshot = snapshot.filter((item) => item.id !== id)
    emit()
  },
  clear() {
    snapshot = []
    emit()
  },
}
export function notify(message, type = 'info') {
  const id = ++nextId
  snapshot = [...snapshot, { id, message: String(message), type }].slice(-5)
  emit()
  return id
}
