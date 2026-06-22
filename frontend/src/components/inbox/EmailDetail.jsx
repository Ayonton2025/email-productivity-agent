import React, { useState } from 'react';
import AttachmentsSection from './AttachmentsSection';

const EmailDetail = ({ email = null, onClose = () => {} }) => {
  const [showFull, setShowFull] = useState(false);

  if (!email) return null;

  // Determine which body to show (prefer HTML)
  const hasHtmlBody = email.body_html && email.body_html.trim().length > 0;
  const bodyContent = hasHtmlBody ? email.body_html : (email.body_text || email.body || 'No content');
  
  // Parse date
  const formatDate = (dateStr) => {
    if (!dateStr) return 'Unknown date';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return dateStr;
    }
  };

  // Extract recipient emails from strings like "Name <email@domain.com>"
  const extractEmail = (str) => {
    if (!str) return str;
    const match = str.match(/<([^>]+)>/);
    return match ? match[1] : str;
  };

  const senderEmail = extractEmail(email.sender);
  const recipients = (email.recipients || []).map(extractEmail);
  const ccRecipients = (email.cc || []).map(extractEmail);

  // Format attachments
  const attachments = email.attachments || [];
  const hasAttachments = attachments.length > 0;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              {email.subject || '(No Subject)'}
            </h2>
            <div className="space-y-1 text-sm text-gray-600">
              <div>
                <span className="font-semibold">From:</span> {email.sender || 'Unknown'}
              </div>
              {recipients.length > 0 && (
                <div>
                  <span className="font-semibold">To:</span> {recipients.join(', ')}
                </div>
              )}
              {ccRecipients.length > 0 && (
                <div>
                  <span className="font-semibold">Cc:</span> {ccRecipients.join(', ')}
                </div>
              )}
              <div>
                <span className="font-semibold">Date:</span> {formatDate(email.received_at)}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label="Close email"
          >
            ×
          </button>
        </div>
      </div>

      {/* AI Category Badge */}
      {email.ai_category && (
        <div className="px-6 py-2 bg-blue-50 border-b">
          <span className="inline-block px-3 py-1 text-xs font-semibold text-blue-700 bg-blue-100 rounded-full">
            {email.ai_category.charAt(0).toUpperCase() + email.ai_category.slice(1)}
          </span>
        </div>
      )}

      {/* Email Body */}
      <div className="flex-1 overflow-auto px-6 py-4">
        <div className="email-body-container">
          {hasHtmlBody ? (
            // Render HTML with sanitization protection
            <div
              className="email-body prose prose-sm max-w-none
                prose-p:my-2 prose-a:text-blue-600 prose-a:underline
                prose-img:max-w-full prose-img:h-auto
                prose-table:border-collapse prose-td:border prose-td:border-gray-300 prose-td:px-3 prose-td:py-2
                prose-pre:bg-gray-100 prose-pre:p-3 prose-code:text-red-600"
              dangerouslySetInnerHTML={{ __html: bodyContent }}
              style={{
                // Limit width and wrap text properly
                maxWidth: '100%',
                wordWrap: 'break-word',
                overflowWrap: 'break-word'
              }}
            />
          ) : (
            // Plain text fallback
            <div className="whitespace-pre-wrap text-gray-700 font-sans text-sm leading-6">
              {bodyContent}
            </div>
          )}
        </div>
      </div>

      {/* Attachments Section - Phase 3 Component */}
      {hasAttachments && (
        <AttachmentsSection emailId={email.id} attachments={attachments} />
      )}

      {/* Footer with Actions */}
      <div className="border-t px-6 py-3 bg-gray-50 flex items-center justify-between">
        <div className="text-xs text-gray-500">
          {email.is_read ? '✓ Read' : 'Unread'} 
          {email.is_flagged && ' • Flagged'}
        </div>
        <div className="space-x-2">
          <button
            className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 transition"
            onClick={() => {
              // Mark as read/unread
              console.log('Toggle read status');
            }}
          >
            {email.is_read ? 'Mark Unread' : 'Mark Read'}
          </button>
          <button
            className={`px-3 py-1 text-sm font-medium rounded transition ${
              email.is_flagged
                ? 'bg-yellow-50 text-yellow-700 border border-yellow-300'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
            onClick={() => {
              // Toggle flag
              console.log('Toggle flag');
            }}
          >
            {email.is_flagged ? '★ Flagged' : '☆ Flag'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default EmailDetail;
