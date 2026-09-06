const requiresTemplateChoice = (user, data) => {
  const plan = (user?.plan || '').toLowerCase()
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser)
  const isFreePlan = !plan || plan === 'personal' || plan === 'free'
  return isFreePlan && (Boolean(data?.mock) || !data?.ai_generated) && !isSuperAdmin
}
import { logger } from '../../utils/logger.js'
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Mail, Clock, AlertCircle, CheckCircle } from 'lucide-react'
import { emailApi, agentApi } from '../../services/api'
import { extractLinksFromEmail } from '../../utils/emailParser.jsx'

import { formatEmailDateLocal, getUserTimeZone } from '../../utils/timezone'
import { useAuth } from '../../context/AuthContext'
const parseAiSummary = (rawSummary) => {
  const raw = typeof rawSummary === 'string' ? rawSummary.trim() : rawSummary
  if (!raw) return { text: '' }

  if (typeof raw === 'object') {
    const tasks = Array.isArray(raw.tasks) ? raw.tasks : []
    return { tasks, meta: raw, text: tasks.length ? '' : JSON.stringify(raw) }
  }

  try {
    const parsed = JSON.parse(raw)
    const tasks = Array.isArray(parsed?.tasks) ? parsed.tasks : []
    return { tasks, meta: parsed, text: tasks.length ? '' : raw }
  } catch {
    return { text: raw }
  }
}
export function useEmailDetail({ email, accountId }) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [processing, setProcessing] = useState(false)
  const [sending, setSending] = useState(false)
  const [reply, setReply] = useState(null)
  const [error, setError] = useState(null)
  const [sendSuccess, setSendSuccess] = useState(false)
  const [showFullBody, setShowFullBody] = useState(false)
  const [expandLinks, setExpandLinks] = useState(false)
  const [mockWarning, setMockWarning] = useState(null)
  const [isAIGenerated, setIsAIGenerated] = useState(false)
  const userTimeZone = getUserTimeZone()
  const formatDate = (d) => formatEmailDateLocal(d)
  const cat = email?.ai_category || email?.category || 'Uncategorized'
  const aiSummaryRaw = email?.ai_summary || email?.summary
  const aiSummary = parseAiSummary(aiSummaryRaw)
  const categoryClass =
    cat === 'Important'
      ? 'badge-important'
      : cat === 'To-Do'
        ? 'badge-todo'
        : cat === 'Newsletter'
          ? 'badge-newsletter'
          : 'badge-default'
  const getPriorityIcon = (p) => {
    const v = (p || '').toLowerCase()
    if (v === 'high') return <AlertCircle className="h-4 w-4 text-red-600" />
    if (v === 'medium') return <Clock className="h-4 w-4 text-amber-600" />
    if (v === 'low') return <CheckCircle className="h-4 w-4 text-emerald-600" />
    return <Mail className="h-4 w-4 text-slate-400" />
  }
  const generateReply = async () => {
    if (!email?.id) return
    setProcessing(true)
    setError(null)
    setReply(null)
    setMockWarning(null)
    setSendSuccess(false)
    try {
      const res = await emailApi.generateReply(email.id)
      if (res.data?.reply) {
        if (requiresTemplateChoice(user, res.data)) {
          const proceedWithTemplate = window.confirm(
            'AI reply is available on paid plans. Click OK to proceed with the template reply, or Cancel to upgrade.'
          )
          if (!proceedWithTemplate) {
            navigate('/billing/upgrade')
            return
          }
        }

        setReply(res.data.reply)
        setIsAIGenerated(res.data?.ai_generated || false)

        // Display mock warning if present
        if (res.data?.mock_warning) {
          setMockWarning(res.data.mock_warning)
          logger.warn('⚠️ Mock reply warning:', res.data.mock_warning)
        }
        return
      }
      const agentRes = await agentApi.processEmail({
        email_id: email.id,
        prompt_type: 'reply_draft',
        email_content: email.body_text || email.body,
        email_subject: email.subject,
        sender: email.sender,
      })
      const data = agentRes.data || {}
      const text = data.result || data.reply || data.message || (typeof data === 'string' ? data : null)
      if (text) {
        setReply(text)
        setIsAIGenerated(true)
      } else setError('Could not generate reply.')
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to generate reply')
      setReply(
        `Dear ${(email.sender || '').split('@')[0]},\n\nThank you for your email regarding "${email?.subject || ''}".\n\nI have received your message and will respond shortly.\n\nBest regards`
      )
    } finally {
      setProcessing(false)
    }
  }
  const sendReply = async () => {
    if (!reply || !accountId) return
    const to = email?.sender
    if (!to) {
      setError('No recipient.')
      return
    }
    setSending(true)
    setError(null)
    setSendSuccess(false)
    try {
      await emailApi.sendEmail(accountId, {
        account_id: accountId,
        to,
        subject: `Re: ${(email?.subject || '').replace(/^Re:\s*/i, '')}`.trim() || 'Re: (no subject)',
        body_text: reply,
        in_reply_to: email?.message_id || null,
        references: Array.isArray(email?.references) ? email.references : [],
        thread_id: email?.thread_id || null,
      })
      setSendSuccess(true)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to send.')
    } finally {
      setSending(false)
    }
  }
  const rawBodyText = email?.body_text || email?.body || ''
  const hasAttachmentMetadata = Array.isArray(email?.attachments) && email.attachments.length > 0
  const emailLinks = extractLinksFromEmail(`${rawBodyText}\n${email?.body_html || ''}`)
  const collapseSource = rawBodyText || String(email?.body_html || '')
  const shouldCollapse = collapseSource.split('\n').length > 35 || collapseSource.length > 3500
  return {
    navigate,
    user,
    processing,
    setProcessing,
    sending,
    setSending,
    reply,
    setReply,
    error,
    setError,
    sendSuccess,
    setSendSuccess,
    showFullBody,
    setShowFullBody,
    expandLinks,
    setExpandLinks,
    mockWarning,
    setMockWarning,
    isAIGenerated,
    setIsAIGenerated,
    userTimeZone,
    formatDate,
    cat,
    aiSummaryRaw,
    aiSummary,
    categoryClass,
    getPriorityIcon,
    generateReply,
    sendReply,
    rawBodyText,
    hasAttachmentMetadata,
    emailLinks,
    collapseSource,
    shouldCollapse,
  }
}
