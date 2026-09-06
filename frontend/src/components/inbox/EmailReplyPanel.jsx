import React from 'react'

import { AlertCircle, MessageSquare, Send, RefreshCw, Loader } from 'lucide-react'

import { EmailBodyRenderer } from '../../utils/emailParser.jsx'

export default function EmailReplyPanel({
  reply,
  generateReply,
  processing,
  mockWarning,
  sendReply,
  sending,
  accountId,
}) {
  return (
    <div className="pt-4 border-t border-slate-200">
      <h3 className="font-semibold text-slate-900 mb-3">AI Reply</h3>
      {!reply ? (
        <button
          type="button"
          onClick={generateReply}
          disabled={processing}
          className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
        >
          {processing ? <Loader className="h-4 w-4 animate-spin" /> : <MessageSquare className="h-4 w-4" />}
          {processing ? 'Generating…' : 'Generate AI Reply'}
        </button>
      ) : (
        <div className="space-y-4">
          {mockWarning && (
            <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm flex items-start gap-2">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">⚠️ Template Response</p>
                <p>{mockWarning}</p>
              </div>
            </div>
          )}
          <div
            className={`p-4 rounded-lg border ${mockWarning ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'}`}
          >
            <EmailBodyRenderer bodyText={reply} className="text-sm" />
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={generateReply}
              disabled={processing}
              className="inline-flex items-center gap-2 px-4 py-2.5 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-100 disabled:opacity-60 transition-colors"
            >
              {processing ? <Loader className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Generate another reply
            </button>
            <button
              type="button"
              onClick={sendReply}
              disabled={sending || !accountId}
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
            >
              {sending ? <Loader className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              {sending ? 'Sending…' : 'Send reply'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
