import EmailLinksPanel from './EmailLinksPanel'
import EmailReplyPanel from './EmailReplyPanel'

import React from 'react'

import { ArrowLeft, Clock, CheckCircle, Eye, ChevronDown, ChevronUp, Paperclip } from 'lucide-react'

import { EmailContentRenderer } from '../../utils/emailParser.jsx'
import AttachmentsSection from './AttachmentsSection'

import { useEmailDetail } from './useEmailDetail'
const EmailDetailPage = ({ email, accountId, onBack }) => {
  const {
    processing,
    sending,
    reply,
    error,
    sendSuccess,
    showFullBody,
    setShowFullBody,
    expandLinks,
    setExpandLinks,
    mockWarning,
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
    shouldCollapse,
  } = useEmailDetail({ email, accountId, onBack })
  return (
    <div className="page-content overflow-hidden flex flex-col">
      <div className="flex items-center gap-4 p-4 border-b border-slate-200 bg-slate-50/80">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 px-3 py-2 text-slate-700 hover:bg-slate-200 rounded-lg transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to inbox
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          <div className="flex justify-between items-start gap-4 flex-wrap">
            <h1 className="text-xl font-bold text-slate-900 break-words">{email?.subject || '(no subject)'}</h1>
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${categoryClass}`}>
              {cat}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm text-slate-600">
            <span className="flex items-center gap-1">
              <span className="font-medium text-slate-700">From:</span>
              {email?.sender}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-4 w-4 text-slate-400" />
              {formatDate(email?.received_at || email?.timestamp)} ({userTimeZone})
            </span>
            {getPriorityIcon(email?.priority)}
            {hasAttachmentMetadata && (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded bg-blue-50 text-blue-700 text-xs font-medium">
                <Paperclip className="h-3 w-3" />
                {email.attachments.length}
              </span>
            )}
          </div>

          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
            <div className={!showFullBody && shouldCollapse ? 'max-h-[520px] overflow-hidden relative' : ''}>
              <EmailContentRenderer
                bodyText={rawBodyText || '(no content)'}
                bodyHtml={email?.body_html}
                className="bg-slate-50"
              />
              {!showFullBody && shouldCollapse && (
                <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-slate-50 to-transparent" />
              )}
            </div>
            {shouldCollapse && (
              <div className="mt-3">
                <button
                  type="button"
                  onClick={() => setShowFullBody((v) => !v)}
                  className="inline-flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
                >
                  {showFullBody ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  {showFullBody ? 'Show less' : 'See more'}
                </button>
              </div>
            )}
          </div>

          {/* Links section if any links are found */}
          <EmailLinksPanel emailLinks={emailLinks} expandLinks={expandLinks} setExpandLinks={setExpandLinks} />

          {aiSummaryRaw ? (
            <div className="p-4 rounded-lg border border-sky-200 bg-sky-50">
              <h3 className="font-semibold text-sky-900 mb-2 flex items-center gap-2">
                <Eye className="h-4 w-4" />
                AI Summary
              </h3>
              {aiSummary?.tasks?.length > 0 ? (
                <div className="space-y-3">
                  <div className="overflow-x-auto rounded-lg border border-sky-200 bg-white">
                    <table className="min-w-full text-sm">
                      <thead className="bg-sky-100 text-sky-900">
                        <tr>
                          <th className="px-3 py-2 text-left font-semibold">Task</th>
                          <th className="px-3 py-2 text-left font-semibold">Deadline</th>
                          <th className="px-3 py-2 text-left font-semibold">Priority</th>
                          <th className="px-3 py-2 text-left font-semibold">Assigned To</th>
                        </tr>
                      </thead>
                      <tbody>
                        {aiSummary.tasks.map((task, idx) => (
                          <tr key={idx} className="border-t border-sky-100 text-slate-700">
                            <td className="px-3 py-2 font-medium">{task?.task || '-'}</td>
                            <td className="px-3 py-2">{task?.deadline || '-'}</td>
                            <td className="px-3 py-2 capitalize">{task?.priority || '-'}</td>
                            <td className="px-3 py-2">{task?.assigned_to || '-'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {aiSummary?.meta?.mock ? (
                    <p className="text-xs text-amber-700">Template summary fallback was used.</p>
                  ) : null}
                </div>
              ) : (
                <p className="text-sky-800 text-sm whitespace-pre-wrap">{aiSummary.text || String(aiSummaryRaw)}</p>
              )}
            </div>
          ) : null}

          <AttachmentsSection
            emailId={email?.id}
            attachments={Array.isArray(email?.attachments) ? email.attachments : []}
          />

          {email?.action_items?.length > 0 ? (
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50">
              <h3 className="font-semibold text-slate-900 mb-3">Action items</h3>
              <ul className="space-y-2">
                {email.action_items.map((item, i) => (
                  <li
                    key={i}
                    className="flex justify-between items-start gap-2 p-2 bg-white rounded border border-slate-200"
                  >
                    <span className="font-medium text-slate-800">{item.task || item}</span>
                    {item.deadline && (
                      <span className="text-xs text-slate-500 flex-shrink-0">
                        Due: {new Date(item.deadline).toLocaleDateString()}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <EmailReplyPanel
            reply={reply}
            generateReply={generateReply}
            processing={processing}
            mockWarning={mockWarning}
            sendReply={sendReply}
            sending={sending}
            accountId={accountId}
          />

          {error && <div className="p-4 rounded-lg border border-red-200 bg-red-50 text-red-800 text-sm">{error}</div>}
          {sendSuccess && (
            <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-800 text-sm flex items-center gap-2">
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
              Reply sent successfully.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
export default EmailDetailPage
