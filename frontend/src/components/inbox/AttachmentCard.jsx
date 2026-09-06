import AttachmentCardView from './AttachmentCardView'
import { logger } from '../../utils/logger.js'
import React, { useState } from 'react'

import attachmentService from '../../services/attachmentService'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

/**
 * AttachmentCard - Individual attachment card with download and analysis trigger
 * Shows file metadata and analysis status
 */
const AttachmentCard = ({ attachment, onAnalysisComplete = () => {} }) => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser)
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [showAnalysis, setShowAnalysis] = useState(false)

  // Handler for download button
  const handleDownload = async () => {
    setDownloading(true)
    setError(null)
    try {
      await attachmentService.downloadAttachmentFile(attachment.id, attachment.filename)
    } catch (err) {
      setError('Download failed')
      logger.error('Download error:', err)
    } finally {
      setDownloading(false)
    }
  }

  // Handler for analyze button
  const handleAnalyze = async () => {
    setLoading(true)
    setError(null)
    try {
      // Trigger analysis
      const result = await attachmentService.triggerAttachmentAnalysis(attachment.id)

      if (result.success) {
        // Analysis triggered successfully
        // Now fetch the analysis (may not be complete immediately)
        setTimeout(() => {
          fetchAnalysis()
        }, 1000)
      } else {
        setLoading(false)
      }
    } catch (err) {
      setError('Failed to trigger analysis')
      logger.error('Analysis trigger error:', err)
      setLoading(false)
    }
  }

  // Fetch analysis results
  const fetchAnalysis = async () => {
    try {
      const result = await attachmentService.getAttachmentAnalysis(attachment.id)
      if (result.success) {
        const analysisData = result.data || {}
        if (analysisData.status === 'not_analyzed') {
          setError('Analysis not yet available. Please try again in a moment.')
          setLoading(false)
          return
        }
        setAnalysis(analysisData)
        setShowAnalysis(true)
        onAnalysisComplete(analysisData)
      } else if (result.data?.status === 'not_analyzed') {
        // Analysis not yet available
        setError('Analysis not yet available. Please try again in a moment.')
        setLoading(false)
      }
    } catch (err) {
      setError('Could not fetch analysis results')
      logger.error('Fetch analysis error:', err)
      setLoading(false)
    }
    setLoading(false)
  }

  const fileSize = attachment.file_size ? attachmentService.formatFileSize(attachment.file_size) : 'Unknown'

  return (
    <AttachmentCardView
      attachment={attachment}
      fileSize={fileSize}
      loading={loading}
      error={error}
      handleDownload={handleDownload}
      downloading={downloading}
      analysis={analysis}
      setShowAnalysis={setShowAnalysis}
      showAnalysis={showAnalysis}
      fetchAnalysis={fetchAnalysis}
      handleAnalyze={handleAnalyze}
      isSuperAdmin={isSuperAdmin}
      navigate={navigate}
    />
  )
}

/**
 * AnalysisDisplay - Shows AI analysis results with tiering
 */

export default AttachmentCard
