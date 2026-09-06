import apiClient from './client'
import { logger } from '../../utils/logger'
export const emailApi = {
  getUserInbox: async (filters = {}) => {
    logger.debug('📧 [Email] Fetching user inbox with filters:', filters)
    try {
      const response = await apiClient.get('/emails/my-inbox', { params: filters })
      logger.debug('✅ [Email] Inbox fetched successfully:', {
        emailsCount: response.data?.length || 0,
        hasEmails: !!response.data && response.data.length > 0,
      })
      return response
    } catch (error) {
      logger.error('❌ [Email] Fetch inbox failed:', error.response?.data)
      throw error
    }
  },

  getEmails: async (limit = 50, offset = 0) => {
    logger.debug('📧 [Email] Fetching emails:', { limit, offset })
    try {
      const response = await apiClient.get(`/emails?limit=${limit}&offset=${offset}`)
      logger.debug('✅ [Email] Emails fetched successfully')
      return response
    } catch (error) {
      logger.error('❌ [Email] Fetch emails failed:', error.response?.data)
      throw error
    }
  },

  generateReply: async (emailId) => {
    logger.debug('📧 [Email] Generating reply for email:', emailId)
    try {
      const response = await apiClient.post(`/emails/${emailId}/generate-reply`)
      logger.debug('✅ [Email] Reply generated successfully')
      return response
    } catch (error) {
      logger.error('❌ [Email] Generate reply failed:', error.response?.data)
      throw error
    }
  },

  getEmail: async (emailId) => {
    logger.debug('📧 [Email] Fetching email:', emailId)
    try {
      const response = await apiClient.get(`/emails/${emailId}`)
      logger.debug('✅ [Email] Email fetched successfully')
      return response
    } catch (error) {
      logger.error('❌ [Email] Fetch email failed:', error.response?.data)
      throw error
    }
  },

  updateEmailCategory: async (emailId, category) => {
    logger.debug('📧 [Email] Updating category:', { emailId, category })
    try {
      const response = await apiClient.put(`/emails/${emailId}/category`, { category })
      logger.debug('✅ [Email] Category updated successfully')
      return response
    } catch (error) {
      logger.error('❌ [Email] Update category failed:', error.response?.data)
      throw error
    }
  },

  syncUserEmails: async () => {
    logger.debug('📧 [Email] Syncing user emails')
    try {
      const response = await apiClient.post('/emails/sync')
      logger.debug('✅ [Email] Email sync initiated')
      return response
    } catch (error) {
      logger.error('❌ [Email] Email sync failed:', error.response?.data)
      throw error
    }
  },

  loadMockEmails: async () => {
    logger.debug('📧 [Email] Loading mock emails')
    try {
      const response = await apiClient.post('/emails/load-mock')
      logger.debug('✅ [Email] Mock emails loaded')
      return response
    } catch (error) {
      logger.error('❌ [Email] Load mock emails failed:', error.response?.data)
      throw error
    }
  },

  // Email Accounts API (IMAP/SMTP based - no OAuth)
  testConnection: (credentials) => apiClient.post('/email-accounts/test-connection', credentials),
  connectAccount: (credentials) => apiClient.post('/email-accounts/connect', credentials),
  getAccounts: () => apiClient.get('/email-accounts/list'),
  getAccountsList: () => apiClient.get('/email-accounts'),
  disconnectAccount: (accountId) => apiClient.delete(`/email-accounts/${accountId}`),
  syncEmails: (accountId, options = {}) => apiClient.post(`/email-accounts/${accountId}/sync`, options),
  getInbox: (accountId, page = 0, perPage = 50) =>
    apiClient.get(`/email-accounts/${accountId}/inbox`, {
      timeout: 120000,
      params: { page, per_page: perPage },
    }),
  getEmailDetail: (accountId, emailId) => apiClient.get(`/email-accounts/${accountId}/email/${emailId}`),
  sendEmail: (accountId, emailData) => apiClient.post(`/email-accounts/${accountId}/send`, emailData),
  getFolders: (accountId) => apiClient.get(`/email-accounts/${accountId}/folders`),
}
