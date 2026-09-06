import { logger } from '../../utils/logger'
export const createWebSocket = (clientId = 'default') => {
  const token = localStorage.getItem('auth_token')
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const configured = import.meta.env.VITE_WS_URL || import.meta.env.VITE_API_URL || window.location.origin
  const baseUrl = configured
    .replace(/^https?:/, protocol)
    .replace(/\/api\/v1\/?$/, '')
    .replace(/\/$/, '')
  const wsUrl = `${baseUrl}/ws/agent?client_id=${clientId}${token ? `&token=${token}` : ''}`
  logger.debug('🔌 [WebSocket] Connecting')
  return new WebSocket(wsUrl)
}
