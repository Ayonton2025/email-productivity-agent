import { useCallback } from 'react'
import { notify } from '../../utils/notifications'
import { logger } from '../../utils/logger.js'
import { useState, useEffect } from 'react'

import { campaignsApi, aiApi } from '../../services/api'

export function useCampaignBuilder({ campaign, onClose, onSave }) {
  const [formData, setFormData] = useState(() => ({
    name: campaign?.name || '',
    description: campaign?.description || '',
    campaign_type: campaign?.campaign_type || 'cold_outreach',
    from_email: campaign?.from_email || '',
    from_name: campaign?.from_name || '',
    reply_to: campaign?.reply_to || '',
    daily_send_limit: campaign?.daily_send_limit || 50,
    send_delay_minutes: campaign?.send_delay_minutes || 5,
    timezone: campaign?.timezone || 'UTC',
    send_hours: campaign?.send_hours || [],
    warm_up_enabled: campaign?.warm_up_enabled ?? false,
    warm_up_emails_per_day: campaign?.warm_up_emails_per_day || 5,
    ab_test_enabled: campaign?.ab_test_enabled ?? false,
    ab_test_split: campaign?.ab_test_split || 0.5,
    tags: campaign?.tags || [],
  }))
  const [sequences, setSequences] = useState(campaign?.sequences || [])
  const [newSequence, setNewSequence] = useState(() => ({
    name: '',
    subject_template: '',
    body_template: '',
    delay_days: 0,
    delay_hours: 0,
    send_if_opened: false,
    send_if_clicked: false,
    send_if_replied: false,
    stop_if_replied: true,
  }))
  const [leads, setLeads] = useState([])
  const [showAddSequence, setShowAddSequence] = useState(false)
  const [showLeadsImport, setShowLeadsImport] = useState(false)
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('basic')
  const [aiGoal, setAiGoal] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [aiMeta, setAiMeta] = useState(() => ({ provider: null, model: null }))
  const [loadingRecommended, setLoadingRecommended] = useState(false)
  const [recommendedSender, setRecommendedSender] = useState(null)
  const aiQuickPrompts = [
    'Create a 3-step cold outreach campaign for SaaS founders',
    'Build a follow-up campaign for warm leads with 2 sequences',
  ]

  const loadRecommendedSender = async () => {
    try {
      const res = await campaignsApi.getRecommendedSender()
      if (res.data?.success && res.data?.recommended) {
        setRecommendedSender(res.data.recommended)
      }
    } catch (error) {
      logger.error('Failed to load recommended sender:', error)
    }
  }
  const applyRecommendedSender = () => {
    if (!recommendedSender) return
    setFormData((prev) => ({
      ...prev,
      from_email: recommendedSender.email,
      from_name: recommendedSender.from_name,
      reply_to: recommendedSender.reply_to,
    }))
  }
  const loadLeads = useCallback(async () => {
    if (!campaign?.id) return
    try {
      const res = await campaignsApi.getLeads(campaign.id)
      setLeads(res.data || [])
    } catch (error) {
      logger.error('Failed to load leads:', error)
    }
  }, [campaign?.id])
  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }))
  }
  const addSequence = async () => {
    if (!newSequence.name || !newSequence.subject_template || !newSequence.body_template) {
      notify('Please fill in all required sequence fields')
      return
    }

    if (campaign?.id) {
      try {
        const sequence = await campaignsApi.createSequence(campaign.id, {
          ...newSequence,
          step_order: sequences.length + 1,
        })
        setSequences([...sequences, sequence.data])
      } catch (error) {
        logger.error('Failed to create sequence:', error)
        notify('Failed to create sequence', 'error')
        return
      }
    } else {
      const sequence = {
        ...newSequence,
        step_order: sequences.length + 1,
        id: `temp-${Date.now()}`,
      }
      setSequences([...sequences, sequence])
    }

    setNewSequence({
      name: '',
      subject_template: '',
      body_template: '',
      delay_days: 0,
      delay_hours: 0,
      send_if_opened: false,
      send_if_clicked: false,
      send_if_replied: false,
      stop_if_replied: true,
    })
    setShowAddSequence(false)
  }
  const removeSequence = async (index, sequenceId) => {
    if (sequenceId && !sequenceId.toString().startsWith('temp-')) {
      // TODO: Delete from API if needed
    }
    setSequences(sequences.filter((_, i) => i !== index))
  }
  const handleBulkImport = async (csvText) => {
    // Parse CSV
    const lines = csvText.split('\n').filter((line) => line.trim())
    const headers = lines[0].split(',').map((h) => h.trim().toLowerCase())
    const importedLeads = []

    for (let i = 1; i < lines.length; i++) {
      const values = lines[i].split(',').map((v) => v.trim())
      const lead = {
        email: values[headers.indexOf('email')] || '',
        first_name: values[headers.indexOf('first_name')] || values[headers.indexOf('firstname')] || '',
        last_name: values[headers.indexOf('last_name')] || values[headers.indexOf('lastname')] || '',
        company: values[headers.indexOf('company')] || '',
        job_title: values[headers.indexOf('job_title')] || values[headers.indexOf('jobtitle')] || '',
        custom_fields: {},
      }
      if (lead.email) importedLeads.push(lead)
    }

    if (campaign?.id && importedLeads.length > 0) {
      try {
        await campaignsApi.bulkCreateLeads(campaign.id, importedLeads)
        await loadLeads()
        setShowLeadsImport(false)
        notify(`Imported ${importedLeads.length} leads`)
      } catch (error) {
        logger.error('Failed to import leads:', error)
        notify('Failed to import leads', 'error')
      }
    } else {
      setLeads([...leads, ...importedLeads])
      setShowLeadsImport(false)
    }
  }
  const handleSave = async () => {
    if (!formData.name || !formData.from_email) {
      notify('Please fill in required fields (Name and From Email)')
      return
    }

    setSaving(true)
    try {
      let savedCampaign
      if (campaign?.id) {
        savedCampaign = await campaignsApi.updateCampaign(campaign.id, formData)
      } else {
        savedCampaign = (await campaignsApi.createCampaign(formData)).data

        // Create sequences
        for (const seq of sequences) {
          await campaignsApi.createSequence(savedCampaign.id, {
            ...seq,
            campaign_id: savedCampaign.id,
          })
        }

        // Import leads if any
        if (leads.length > 0) {
          await campaignsApi.bulkCreateLeads(savedCampaign.id, leads)
        }
      }

      onSave()
      onClose()
    } catch (error) {
      logger.error('Failed to save campaign:', error)
      notify('Failed to save campaign', 'error')
    } finally {
      setSaving(false)
    }
  }
  const handleGenerateAIDraft = async (goal) => {
    if (!goal?.trim()) return
    setAiLoading(true)
    setAiError('')
    try {
      const res = await aiApi.assistWorkspace({
        page: 'campaigns',
        objective: goal.trim(),
        mode: 'draft',
        context: {
          existing_sequences: sequences.length,
          existing_leads: leads.length,
          current_form: formData,
        },
      })
      const draft = res.data?.draft || {}
      setAiMeta({ provider: res.data?.provider, model: res.data?.model })
      if (draft.campaign) {
        setFormData((prev) => ({ ...prev, ...draft.campaign }))
      }
      if (Array.isArray(draft.sequences) && draft.sequences.length > 0) {
        setSequences(
          draft.sequences.map((seq, idx) => ({ ...seq, step_order: idx + 1, id: `temp-ai-${Date.now()}-${idx}` }))
        )
      }
      if (Array.isArray(draft.leads) && draft.leads.length > 0) {
        setLeads(draft.leads)
      }
    } catch (error) {
      const detail =
        error?.response?.data?.detail ||
        error?.response?.data?.error ||
        error?.message ||
        'Failed to generate campaign draft'
      setAiError(detail)
    } finally {
      setAiLoading(false)
    }
  }
  useEffect(() => {
    if (campaign?.id) {
      loadLeads()
    }
    // Load recommended sender on mount
    loadRecommendedSender()
  }, [campaign?.id, loadLeads])
  return {
    formData,
    setFormData,
    sequences,
    setSequences,
    newSequence,
    setNewSequence,
    leads,
    setLeads,
    showAddSequence,
    setShowAddSequence,
    showLeadsImport,
    setShowLeadsImport,
    saving,
    setSaving,
    activeTab,
    setActiveTab,
    aiGoal,
    setAiGoal,
    aiLoading,
    setAiLoading,
    aiError,
    setAiError,
    aiMeta,
    setAiMeta,
    loadingRecommended,
    setLoadingRecommended,
    recommendedSender,
    setRecommendedSender,
    aiQuickPrompts,
    loadRecommendedSender,
    applyRecommendedSender,
    loadLeads,
    handleInputChange,
    addSequence,
    removeSequence,
    handleBulkImport,
    handleSave,
    handleGenerateAIDraft,
  }
}
