export const getSeverityColor = (severity) => {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'high':
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case 'medium':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    case 'low':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

export const getStatusColor = (status) => {
  switch (status?.toLowerCase()) {
    case 'new':
      return 'bg-blue-100 text-blue-800'
    case 'qualified':
      return 'bg-purple-100 text-purple-800'
    case 'in_progress':
      return 'bg-yellow-100 text-yellow-800'
    case 'won':
      return 'bg-green-100 text-green-800'
    case 'lost':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

export const formatDate = (dateString) => {
  if (!dateString) return 'No date'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export const isOverdue = (deadline) => {
  if (!deadline) return false
  return new Date(deadline) < new Date()
}
