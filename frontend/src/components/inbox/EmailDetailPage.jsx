import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Mail,
  Clock,
  AlertCircle,
  CheckCircle,
  MessageSquare,
  Send,
  RefreshCw,
  Loader,
  Eye,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Paperclip,
} from 'lucide-react';
import { emailApi, agentApi } from '../../services/api';
import { EmailBodyRenderer, EmailContentRenderer, extractLinksFromEmail, shortenUrl } from '../../utils/emailParser.jsx';
import AttachmentsSection from './AttachmentsSection';
import { formatEmailDateLocal, getUserTimeZone } from '../../utils/timezone';
import { useAuth } from '../../context/AuthContext';

const parseAiSummary = (rawSummary) => {
  const raw = typeof rawSummary === 'string' ? rawSummary.trim() : rawSummary;
  if (!raw) return { text: '' };

  if (typeof raw === 'object') {
    const tasks = Array.isArray(raw.tasks) ? raw.tasks : [];
    return { tasks, meta: raw, text: tasks.length ? '' : JSON.stringify(raw) };
  }

  try {
    const parsed = JSON.parse(raw);
    const tasks = Array.isArray(parsed?.tasks) ? parsed.tasks : [];
    return { tasks, meta: parsed, text: tasks.length ? '' : raw };
  } catch {
    return { text: raw };
  }
};

const EmailDetailPage = ({ email, accountId, onBack }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [processing, setProcessing] = useState(false);
  const [sending, setSending] = useState(false);
  const [reply, setReply] = useState(null);
  const [error, setError] = useState(null);
  const [sendSuccess, setSendSuccess] = useState(false);
  const [showFullBody, setShowFullBody] = useState(false);
  const [expandLinks, setExpandLinks] = useState(false);
  const [mockWarning, setMockWarning] = useState(null);
  const [isAIGenerated, setIsAIGenerated] = useState(false);
  const userTimeZone = getUserTimeZone();

  const formatDate = (d) => formatEmailDateLocal(d);

  const cat = email?.ai_category || email?.category || 'Uncategorized';
  const aiSummaryRaw = email?.ai_summary || email?.summary;
  const aiSummary = parseAiSummary(aiSummaryRaw);
  const categoryClass =
    cat === 'Important'
      ? 'badge-important'
      : cat === 'To-Do'
      ? 'badge-todo'
      : cat === 'Newsletter'
      ? 'badge-newsletter'
      : 'badge-default';

  const getPriorityIcon = (p) => {
    const v = (p || '').toLowerCase();
    if (v === 'high') return <AlertCircle className="h-4 w-4 text-red-600" />;
    if (v === 'medium') return <Clock className="h-4 w-4 text-amber-600" />;
    if (v === 'low') return <CheckCircle className="h-4 w-4 text-emerald-600" />;
    return <Mail className="h-4 w-4 text-slate-400" />;
  };

  const generateReply = async () => {
    if (!email?.id) return;
    setProcessing(true);
    setError(null);
    setReply(null);
    setMockWarning(null);
    setSendSuccess(false);
    try {
      const res = await emailApi.generateReply(email.id);
      if (res.data?.reply) {
        const plan = (user?.plan || '').toLowerCase();
        const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
        const isFreePlan = !plan || plan === 'personal' || plan === 'free';
        const isMockReply = Boolean(res.data?.mock) || !Boolean(res.data?.ai_generated);
        if (isFreePlan && isMockReply && !isSuperAdmin) {
          const proceedWithTemplate = window.confirm(
            'AI reply is available on paid plans. Click OK to proceed with the template reply, or Cancel to upgrade.'
          );
          if (!proceedWithTemplate) {
            navigate('/billing/upgrade');
            return;
          }
        }

        setReply(res.data.reply);
        setIsAIGenerated(res.data?.ai_generated || false);
        
        // Display mock warning if present
        if (res.data?.mock_warning) {
          setMockWarning(res.data.mock_warning);
          console.warn('⚠️ Mock reply warning:', res.data.mock_warning);
        }
        return;
      }
      const agentRes = await agentApi.processEmail({
        email_id: email.id,
        prompt_type: 'reply_draft',
        email_content: email.body_text || email.body,
        email_subject: email.subject,
        sender: email.sender,
      });
      const data = agentRes.data || {};
      const text =
        data.result || data.reply || data.message || (typeof data === 'string' ? data : null);
      if (text) {
        setReply(text);
        setIsAIGenerated(true);
      }
      else setError('Could not generate reply.');
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to generate reply');
      setReply(
        `Dear ${(email.sender || '').split('@')[0]},\n\nThank you for your email regarding "${email?.subject || ''}".\n\nI have received your message and will respond shortly.\n\nBest regards`
      );
    } finally {
      setProcessing(false);
    }
  };

  const sendReply = async () => {
    if (!reply || !accountId) return;
    const to = email?.sender;
    if (!to) {
      setError('No recipient.');
      return;
    }
    setSending(true);
    setError(null);
    setSendSuccess(false);
    try {
      await emailApi.sendEmail(accountId, {
        account_id: accountId,
        to,
        subject: `Re: ${(email?.subject || '').replace(/^Re:\s*/i, '')}`.trim() || 'Re: (no subject)',
        body_text: reply,
        in_reply_to: email?.message_id || null,
        references: Array.isArray(email?.references) ? email.references : [],
        thread_id: email?.thread_id || null,
      });
      setSendSuccess(true);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Failed to send.');
    } finally {
      setSending(false);
    }
  };

  const rawBodyText = email?.body_text || email?.body || '';
  const hasAttachmentMetadata = Array.isArray(email?.attachments) && email.attachments.length > 0;
  const emailLinks = extractLinksFromEmail(`${rawBodyText}\n${email?.body_html || ''}`);
  const collapseSource = rawBodyText || String(email?.body_html || '');
  const shouldCollapse = (collapseSource.split('\n').length > 35) || (collapseSource.length > 3500);

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
            <h1 className="text-xl font-bold text-slate-900 break-words">
              {email?.subject || '(no subject)'}
            </h1>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${categoryClass}`}
            >
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
          {emailLinks.length > 0 && (
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50">
              <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
                <ExternalLink className="h-4 w-4" />
                Links in this email ({emailLinks.length})
              </h3>
              <ul className="space-y-2">
                {/* Show first 2 links always */}
                {emailLinks.slice(0, 2).map((link, idx) => (
                  <li key={idx} className="flex items-start gap-2 p-2 bg-white rounded border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all">
                    <a
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline visited:text-purple-600 text-sm transition-colors flex-1 break-all"
                      title={link}
                    >
                      {shortenUrl(link, 48)}
                    </a>
                  </li>
                ))}
                
                {/* Show remaining links only if expanded */}
                {expandLinks && emailLinks.slice(2).map((link, idx) => (
                  <li key={idx + 2} className="flex items-start gap-2 p-2 bg-white rounded border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all animate-fadeIn">
                    <a
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline visited:text-purple-600 text-sm transition-colors flex-1 break-all"
                      title={link}
                    >
                      {shortenUrl(link, 48)}
                    </a>
                  </li>
                ))}

                {/* Show "Open more" button if there are more than 2 links */}
                {emailLinks.length > 2 && (
                  <button
                    type="button"
                    onClick={() => setExpandLinks(!expandLinks)}
                    className="w-full mt-2 py-2 px-3 text-sm font-medium text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded border border-indigo-200 hover:border-indigo-300 transition-colors flex items-center justify-center gap-2"
                  >
                    {expandLinks ? (
                      <>
                        <ChevronUp className="h-4 w-4" />
                        Hide {emailLinks.length - 2} more link{emailLinks.length !== 3 ? 's' : ''}
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-4 w-4" />
                        Open {emailLinks.length - 2} more link{emailLinks.length !== 3 ? 's' : ''}
                      </>
                    )}
                  </button>
                )}
              </ul>
            </div>
          )}

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

          <div className="pt-4 border-t border-slate-200">
            <h3 className="font-semibold text-slate-900 mb-3">AI Reply</h3>
            {!reply ? (
              <button
                type="button"
                onClick={generateReply}
                disabled={processing}
                className="inline-flex items-center gap-2 px-4 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
              >
                {processing ? (
                  <Loader className="h-4 w-4 animate-spin" />
                ) : (
                  <MessageSquare className="h-4 w-4" />
                )}
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
                <div className={`p-4 rounded-lg border ${mockWarning ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'}`}>
                  <EmailBodyRenderer 
                    bodyText={reply}
                    className="text-sm"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={generateReply}
                    disabled={processing}
                    className="inline-flex items-center gap-2 px-4 py-2.5 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-100 disabled:opacity-60 transition-colors"
                  >
                    {processing ? (
                      <Loader className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4" />
                    )}
                    Generate another reply
                  </button>
                  <button
                    type="button"
                    onClick={sendReply}
                    disabled={sending || !accountId}
                    className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 text-white font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                  >
                    {sending ? (
                      <Loader className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    {sending ? 'Sending…' : 'Send reply'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="p-4 rounded-lg border border-red-200 bg-red-50 text-red-800 text-sm">
              {error}
            </div>
          )}
          {sendSuccess && (
            <div className="p-4 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-800 text-sm flex items-center gap-2">
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
              Reply sent successfully.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmailDetailPage;
