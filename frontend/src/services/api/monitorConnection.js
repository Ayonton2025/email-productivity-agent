import { logger } from '../../utils/logger'
import { testConnection } from './testConnection'
export const monitorConnection = () => {
  const checkInterval = setInterval(async () => {
    const status = await testConnection()
    if (!status.success) {
      logger.warn('⚠️ [Monitor] Backend connection lost')
    }
  }, 30000)
  return () => clearInterval(checkInterval)
}
