import { logger } from '../../utils/logger'
export const tokenUtils = {
  getToken: () => {
    const token = localStorage.getItem('auth_token')
    logger.debug('🔍 [Token] Retrieved token:', token ? 'Present' : 'None')
    return token
  },
  setToken: (token) => {
    logger.debug('💾 [Token] Storing token in localStorage:', token ? 'Present' : 'Empty token!')
    if (!token) {
      logger.error('❌ [Token] Attempted to store empty token!')
      return
    }
    localStorage.setItem('auth_token', token)
  },
  removeToken: () => {
    logger.debug('🗑️ [Token] Removing token from localStorage')
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
  },
  isValid: () => {
    const token = localStorage.getItem('auth_token')
    const isValid = !!token
    logger.debug('🔍 [Token] Validation check:', isValid ? 'Valid' : 'Invalid')
    return isValid
  },
}
