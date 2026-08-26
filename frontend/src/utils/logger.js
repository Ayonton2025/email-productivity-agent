const isDevelopment = import.meta.env.DEV

const emit = (level, args) => {
  if (!isDevelopment || typeof window === 'undefined') return
  window.dispatchEvent(
    new CustomEvent('bylix:log', {
      detail: { level, args, timestamp: new Date().toISOString() },
    })
  )
}

export const logger = {
  debug: (...args) => emit('debug', args),
  info: (...args) => emit('info', args),
  warn: (...args) => emit('warn', args),
  error: (...args) => emit('error', args),
}
