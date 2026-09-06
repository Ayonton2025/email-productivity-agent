import { useEffect, useState } from 'react'

import { sharedInboxApi } from '../../services/api'
import { getSubscription } from '../../services/paymentService'
import { useAuth } from '../../context/AuthContext'

export function useSharedInbox() {
  const { user } = useAuth()
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser)
  const [loading, setLoading] = useState(true)
  const [inboxes, setInboxes] = useState([])
  const [selectedInbox, setSelectedInbox] = useState(null)
  const [members, setMembers] = useState([])
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [createForm, setCreateForm] = useState({ name: '', description: '' })
  const [memberEmail, setMemberEmail] = useState('')
  const [emailIdToAdd, setEmailIdToAdd] = useState('')
  const [subscription, setSubscription] = useState(null)
  const [subscriptionLoadFailed, setSubscriptionLoadFailed] = useState(false)
  const [assignedToMeOnly, setAssignedToMeOnly] = useState(false)
  const loadInboxes = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await sharedInboxApi.list()
      const items = res.data?.items || []
      setInboxes(items)
      if (items.length > 0) setSelectedInbox((previous) => previous || items[0])
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load shared inboxes')
    } finally {
      setLoading(false)
    }
  }
  const loadInboxDetails = async (inboxId) => {
    try {
      const [mRes, eRes] = await Promise.all([sharedInboxApi.listMembers(inboxId), sharedInboxApi.listEmails(inboxId)])
      setMembers(mRes.data?.members || [])
      setItems(eRes.data?.items || [])
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to load shared inbox details')
    }
  }
  useEffect(() => {
    loadInboxes()
  }, [])
  useEffect(() => {
    const loadSubscription = async () => {
      try {
        const data = await getSubscription()
        setSubscription(data || null)
        setSubscriptionLoadFailed(false)
      } catch (_e) {
        setSubscription(null)
        setSubscriptionLoadFailed(true)
      }
    }
    loadSubscription()
  }, [])
  useEffect(() => {
    if (selectedInbox?.id) loadInboxDetails(selectedInbox.id)
  }, [selectedInbox?.id])
  const sharedInboxPlanLimits = {
    team: 5,
    enterprise: 100,
  }
  const currentPlanId = subscription?.plan_id || null
  const hasSharedInboxFeature = isSuperAdmin || currentPlanId === 'team' || currentPlanId === 'enterprise'
  const sharedInboxLimit = currentPlanId ? sharedInboxPlanLimits[currentPlanId] || 0 : 0
  const ownedInboxCount = inboxes.filter((i) => i.member_role === 'owner').length
  const selectedRole = selectedInbox?.member_role || null
  const canManageMembers = selectedRole === 'owner' || selectedRole === 'admin'
  const teamMemberLimit = Number(subscription?.team_members_limit || 0)
  const memberCount = members.length
  const createInbox = async () => {
    if (!createForm.name.trim()) return
    setError('')
    setSuccess('')

    if (!isSuperAdmin && !subscriptionLoadFailed && !hasSharedInboxFeature) {
      setError('Your current plan does not include shared inbox. Upgrade to Team or Enterprise.')
      return
    }
    if (!isSuperAdmin && !subscriptionLoadFailed && ownedInboxCount >= sharedInboxLimit) {
      setError(`Plan limit reached: ${sharedInboxLimit} shared inbox(es) allowed.`)
      return
    }

    try {
      await sharedInboxApi.create(createForm)
      setCreateForm({ name: '', description: '' })
      setSuccess('Shared inbox created.')
      await loadInboxes()
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to create shared inbox')
    }
  }
  const addMember = async () => {
    if (!selectedInbox?.id || !memberEmail.trim()) return
    setError('')
    setSuccess('')

    if (!canManageMembers) {
      setError('Only owner or admin can add members to this shared inbox.')
      return
    }
    if (!isSuperAdmin && !subscriptionLoadFailed && !hasSharedInboxFeature) {
      setError('Your current plan does not include shared inbox. Upgrade to Team or Enterprise.')
      return
    }
    if (!isSuperAdmin && !subscriptionLoadFailed && teamMemberLimit > 0 && memberCount >= teamMemberLimit) {
      setError(`Team seat limit reached: ${teamMemberLimit} member(s) allowed for your plan.`)
      return
    }

    try {
      await sharedInboxApi.addMember(selectedInbox.id, { user_email: memberEmail.trim() })
      setMemberEmail('')
      setSuccess('Member added to shared inbox.')
      await loadInboxDetails(selectedInbox.id)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to add member')
    }
  }
  const addEmail = async () => {
    if (!selectedInbox?.id || !emailIdToAdd.trim()) return
    setError('')
    setSuccess('')
    try {
      await sharedInboxApi.addEmail(selectedInbox.id, emailIdToAdd.trim())
      setEmailIdToAdd('')
      setSuccess('Email added to shared inbox.')
      await loadInboxDetails(selectedInbox.id)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to add email')
    }
  }
  const setStatus = async (emailId, status) => {
    if (!selectedInbox?.id) return
    try {
      await sharedInboxApi.updateEmail(selectedInbox.id, emailId, { status })
      await loadInboxDetails(selectedInbox.id)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to update status')
    }
  }
  const setAssignment = async (emailId, assignedToUserEmail) => {
    if (!selectedInbox?.id) return
    setError('')
    if (!canManageMembers) {
      setError('Only owner or admin can assign inbox items.')
      return
    }
    try {
      await sharedInboxApi.updateEmail(selectedInbox.id, emailId, { assigned_to_user_email: assignedToUserEmail })
      await loadInboxDetails(selectedInbox.id)
    } catch (e) {
      setError(e?.response?.data?.detail || 'Failed to update assignee')
    }
  }
  const memberEmailById = members.reduce((acc, m) => {
    acc[m.user_id] = m.email
    return acc
  }, {})
  const memberDisplayByEmail = members.reduce((acc, m) => {
    acc[m.email] = m.full_name || m.email
    return acc
  }, {})
  const currentUserId = user?.id || null
  const currentUserEmail = user?.email || null
  const currentMember = members.find((m) => m.email === currentUserEmail)
  const currentMemberId = currentMember?.user_id || null
  const filteredItems = assignedToMeOnly
    ? items.filter((item) => {
        const assignee = item?.shared?.assigned_to_user_id
        if (!assignee) return false
        return assignee === currentUserId || assignee === currentMemberId
      })
    : items
  return {
    user,
    isSuperAdmin,
    loading,
    setLoading,
    inboxes,
    setInboxes,
    selectedInbox,
    setSelectedInbox,
    members,
    setMembers,
    items,
    setItems,
    error,
    setError,
    success,
    setSuccess,
    createForm,
    setCreateForm,
    memberEmail,
    setMemberEmail,
    emailIdToAdd,
    setEmailIdToAdd,
    subscription,
    setSubscription,
    subscriptionLoadFailed,
    setSubscriptionLoadFailed,
    assignedToMeOnly,
    setAssignedToMeOnly,
    loadInboxes,
    loadInboxDetails,
    sharedInboxPlanLimits,
    currentPlanId,
    hasSharedInboxFeature,
    sharedInboxLimit,
    ownedInboxCount,
    selectedRole,
    canManageMembers,
    teamMemberLimit,
    memberCount,
    createInbox,
    addMember,
    addEmail,
    setStatus,
    setAssignment,
    memberEmailById,
    memberDisplayByEmail,
    currentUserId,
    currentUserEmail,
    currentMember,
    currentMemberId,
    filteredItems,
  }
}
