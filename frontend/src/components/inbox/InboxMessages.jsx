import InboxEmailCard from './InboxEmailCard'

import React from 'react'

import { RefreshCw, Mail, Paperclip } from 'lucide-react'

export default function InboxMessages({
  loading,
  sortedEmails,
  viewMode,
  groupedByCategory,
  openEmail,
  getPriorityIcon,
  formatDate,
  badgeClass,
}) {
  return (
    <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
      {/* Background loading indicator */}
      {loading && sortedEmails.length > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-b border-blue-200 flex items-center gap-2">
          <RefreshCw className="h-4 w-4 animate-spin text-blue-600" />
          <span className="text-sm text-blue-700 font-medium">Loading new messages...</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto page-content">
        {sortedEmails.length === 0 && !loading ? (
          <div className="text-center py-16 text-slate-500">
            <Mail className="h-12 w-12 mx-auto mb-4 text-slate-300" />
            <p className="font-medium text-slate-700">No emails found</p>
            <p className="text-sm mt-1">Connect an account and sync, or load mock data</p>
          </div>
        ) : sortedEmails.length === 0 && loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="h-8 w-8 animate-spin text-slate-400" />
              <p className="text-slate-600 font-medium">Loading your inbox...</p>
            </div>
          </div>
        ) : viewMode === 'grouped' ? (
          <div className="divide-y divide-slate-200">
            {groupedByCategory.map(({ category, emails: groupEmails }) => (
              <div key={category}>
                <div className="px-4 py-2 bg-slate-100 border-l-4 border-indigo-500 font-medium text-slate-900 flex justify-between items-center">
                  <span>{category}</span>
                  <span className="text-xs text-slate-500">
                    {groupEmails.length} email{groupEmails.length !== 1 ? 's' : ''}
                  </span>
                </div>
                {groupEmails.map((email) => {
                  const cat = email.ai_category || email.category || 'Uncategorized'
                  const preview = (email.body_text || email.body || '').trim().slice(0, 80)
                  return (
                    <InboxEmailCard
                      key={email.id}
                      email={email}
                      openEmail={openEmail}
                      getPriorityIcon={getPriorityIcon}
                      preview={preview}
                      formatDate={formatDate}
                      badgeClass={badgeClass}
                      cat={cat}
                    />
                  )
                })}
              </div>
            ))}
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {sortedEmails.map((email) => {
              const cat = email.ai_category || email.category || 'Uncategorized'
              const preview = (email.body_text || email.body || '').trim().slice(0, 80)
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
                  <span
                    className={`inbox-badge inline-flex px-2 py-0.5 rounded text-xs font-medium ${badgeClass(cat)}`}
                  >
                    Category: {cat}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
