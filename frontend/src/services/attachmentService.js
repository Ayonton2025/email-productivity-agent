import apiClient from './api';

/**
 * AttachmentService - API calls for attachment and document analysis operations
 * Integrates with backend Phase 1 & 2 (attachment extraction and AI analysis)
 */

class AttachmentService {
  // ==================== SINGLE ATTACHMENT OPERATIONS ====================
  
  /**
   * Get attachment metadata
   * @param {string} attachmentId - ID of attachment to fetch
   * @returns {Promise} Attachment info with download URL
   */
  async getAttachmentInfo(attachmentId) {
    try {
      const response = await apiClient.get(`/attachments/${attachmentId}/info`);
      console.log('✅ [AttachmentService] Retrieved attachment info:', attachmentId);
      return response.data;
    } catch (error) {
      console.error('❌ [AttachmentService] Error getting attachment info:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Download attachment file
   * @param {string} attachmentId - ID of attachment to download
   * @returns {Promise} File blob
   */
  async downloadAttachment(attachmentId) {
    try {
      const response = await apiClient.get(`/attachments/${attachmentId}/download`, {
        responseType: 'blob' // Request as blob for file download
      });
      console.log('✅ [AttachmentService] Downloaded attachment:', attachmentId);
      return response.data;
    } catch (error) {
      console.error('❌ [AttachmentService] Error downloading attachment:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Get AI analysis of attachment
   * Returns tiered results based on user plan (free = metadata, paid = full analysis)
   * @param {string} attachmentId - ID of attachment to analyze
   * @returns {Promise} Analysis results with tiering applied
   */
  async getAttachmentAnalysis(attachmentId) {
    try {
      const response = await apiClient.get(`/attachments/${attachmentId}/analysis`);
      console.log('✅ [AttachmentService] Retrieved attachment analysis:', attachmentId);
      return response.data;
    } catch (error) {
      console.error('❌ [AttachmentService] Error getting attachment analysis:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Trigger AI analysis on attachment (async, runs in background)
   * @param {string} attachmentId - ID of attachment to analyze
   * @returns {Promise} Task queued confirmation
   */
  async triggerAttachmentAnalysis(attachmentId) {
    try {
      const response = await apiClient.post(`/attachments/${attachmentId}/analyze`);
      console.log('✅ [AttachmentService] Triggered attachment analysis:', attachmentId);
      return response.data;
    } catch (error) {
      console.error('❌ [AttachmentService] Error triggering attachment analysis:', error);
      throw this._handleError(error);
    }
  }

  // ==================== EMAIL-LEVEL BATCH OPERATIONS ====================

  /**
   * List all attachments for an email with optional analysis status
   * @param {string} emailId - ID of email
   * @param {boolean} includeAnalysis - Whether to include analysis status
   * @returns {Promise} Array of attachments with metadata
   */
  async getEmailAttachments(emailId, includeAnalysis = false) {
    try {
      const params = includeAnalysis ? { include_analysis: true } : {};
      const response = await apiClient.get(`/emails/${emailId}/attachments`, { params });
      console.log('✅ [AttachmentService] Retrieved email attachments:', emailId);
      return response.data;
    } catch (error) {
      console.error('❌ [AttachmentService] Error getting email attachments:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Get attachment count for UI badges
   * @param {string} emailId - ID of email
   * @returns {Promise} Count of attachments
   */
  async getEmailAttachmentCount(emailId) {
    try {
      const response = await apiClient.get(`/emails/${emailId}/attachments/count`);
      console.log('✅ [AttachmentService] Retrieved attachment count:', emailId);
      return response.data;
    } catch (error) {
      console.error('❌ [AttachmentService] Error getting attachment count:', error);
      throw this._handleError(error);
    }
  }

  /**
   * Trigger AI analysis on all attachments in an email
   * @param {string} emailId - ID of email
   * @returns {Promise} Batch task queued confirmation
   */
  async analyzeEmailAttachments(emailId) {
    try {
      const response = await apiClient.post(`/emails/${emailId}/attachments/analyze-all`);
      console.log('✅ [AttachmentService] Triggered batch email analysis:', emailId);
      return response.data;
    } catch (error) {
      console.error('❌ [AttachmentService] Error analyzing email attachments:', error);
      throw this._handleError(error);
    }
  }

  // ==================== UTILITY METHODS ====================

  /**
   * Handle common API errors with user-friendly messages
   */
  _handleError(error) {
    if (error.response?.status === 404) {
      return { error: 'Attachment or analysis not found' };
    } else if (error.response?.status === 403) {
      return { error: 'You do not have permission to access this attachment' };
    } else if (error.response?.status === 401) {
      return { error: 'Please log in again to access attachments' };
    } else if (error.response?.status === 500) {
      return { error: 'Server error processing attachment' };
    } else if (error.message === 'Network Error') {
      return { error: 'Network error - check your connection' };
    }
    return { error: error.message || 'Failed to process attachment' };
  }

  /**
   * Download attachment by triggering browser download
   */
  async downloadAttachmentFile(attachmentId, filename) {
    try {
      const blob = await this.downloadAttachment(attachmentId);
      
      // Create blob URL and trigger download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || 'attachment';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      console.log('✅ [AttachmentService] File download initiated:', filename);
    } catch (error) {
      console.error('❌ [AttachmentService] Error initiating download:', error);
      throw error;
    }
  }

  /**
   * Format file size for display
   */
  formatFileSize(bytes) {
    if (!bytes || bytes === 0) return 'Unknown';
    const units = ['B', 'KB', 'MB', 'GB'];
    const size = Math.abs(bytes);
    let unitIndex = 0;
    let fileSize = size;
    while (fileSize >= 1024 && unitIndex < units.length - 1) {
      fileSize /= 1024;
      unitIndex++;
    }
    return `${fileSize.toFixed(1)} ${units[unitIndex]}`;
  }

  /**
   * Get file extension from filename
   */
  getFileExtension(filename) {
    if (!filename) return '';
    const parts = filename.split('.');
    return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : '';
  }

  /**
   * Get file icon name based on extension
   */
  getFileIcon(filename) {
    const ext = this.getFileExtension(filename);
    const iconMap = {
      pdf: 'FileText',
      doc: 'FileText',
      docx: 'FileText',
      txt: 'FileText',
      csv: 'FileText',
      xls: 'FileText',
      xlsx: 'FileText',
      zip: 'Archive',
      rar: 'Archive',
      jpg: 'Image',
      jpeg: 'Image',
      png: 'Image',
      gif: 'Image',
      mp4: 'Video',
      mov: 'Video',
      mp3: 'Music',
      wav: 'Music'
    };
    return iconMap[ext] || 'FileText';
  }
}

export default new AttachmentService();
