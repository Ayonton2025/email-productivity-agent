import React from 'react'

import { Paperclip } from 'lucide-react'

export default function InboxEmailCard({ email, openEmail, getPriorityIcon, preview, formatDate, badgeClass, cat }) {
  return (
    <div
      key={email.id}
      role="button"
      tabIndex={0}
      onClick={() => openEmail(email)}
      onKeyDown={(e) => e.key === 'Enter' && openEmail(email)}
      className={`inbox-row cursor-pointer ${!email.is_read ? 'unread' : ''}`}
    >
      <div className="inbox-icons">
        {getPriorityIcon(email.priority)}
        {!email.is_read && <div className="w-2 h-2 rounded-full bg-blue-500" />}
      </div>
      <div className="inbox-main">
        <div className="subject">{email.subject || '(no subject)'}</div>
        <div className="sender">{email.sender}</div>
        <div className="preview">{preview || '—'}</div>
      </div>
      {((email.attachment_count || 0) > 0 || (email.attachments && email.attachments.length > 0)) && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
          <Paperclip className="h-3 w-3" />
          {email.attachment_count || email.attachments.length}
        </span>
      )}
      <div className="meta">{formatDate(email.received_at || email.timestamp)}</div>
      <span className={`inbox-badge inline-flex px-2 py-0.5 rounded text-xs font-medium ${badgeClass(cat)}`}>
        Category: {cat}
      </span>
    </div>
  )
}
