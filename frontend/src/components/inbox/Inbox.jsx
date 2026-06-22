import React, { useState, useEffect, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  RefreshCw,
  Mail,
  Clock,
  AlertCircle,
  CheckCircle,
  MessageSquare,
  Paperclip,
} from 'lucide-react';
import { EmailContext } from '../../context/EmailContext';
import { emailApi } from '../../services/api';
import { CreditWarningBanner, PremiumPrompt, SubscribeButton } from '../premium/PremiumPrompt';
import { useSubscription } from '../../hooks/useSubscription';
import { useAuth } from '../../context/AuthContext';
import EmailDetailPage from './EmailDetailPage';
import { formatEmailDateLocal, getUserTimeZone } from '../../utils/timezone';

const Inbox = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  const { emails, setEmails } = useContext(EmailContext);
  const { checkCreditLimit, creditWarning, showPremiumPrompt, promptType, closePremiumPrompt, planLimits } = useSubscription();

  const [searchTerm, setSearchTerm] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [viewMode, setViewMode] = useState('list');
  const [view, setView] = useState('list');
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [emailAccounts, setEmailAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creditsUsed, setCreditsUsed] = useState(0);
  const userTimeZone = getUserTimeZone();

  // Reset view to list whenever component is mounted/remounted
  useEffect(() => {
    setView('list');
    setSelectedEmail(null);
  }, []);

  useEffect(() => {
    loadEmailAccounts();
    // Simulate credit usage: 1 credit per email loaded
    const simulatedCredits = Math.min(emails.length, 80);
    setCreditsUsed(simulatedCredits);
    checkCreditLimit(simulatedCredits);
  }, [emails.length]);

  useEffect(() => {
    if (!selectedAccountId) return undefined;
    const intervalId = setInterval(() => {
      loadInbox(selectedAccountId);
    }, 60000);
    return () => clearInterval(intervalId);
  }, [selectedAccountId]);

  const loadEmailAccounts = async () => {
    try {
      const listRes = await emailApi.getAccountsList();
      const accounts = Array.isArray(listRes.data) ? listRes.data : listRes.data?.accounts || [];
      setEmailAccounts(accounts);
      if (accounts.length > 0) {
        const first = accounts[0];
        setSelectedAccountId(first.id);
        loadInbox(first.id);
      }
    } catch (err) {
      console.error('Failed to load email accounts:', err);
    }
  };

  const loadInbox = async (accountId) => {
    setLoading(true);
    try {
      const res = await emailApi.getInbox(accountId);
      const list = res.data?.emails || [];
      setEmails(list);
    } catch (err) {
      console.error('Failed to load inbox:', err);
      const timedOut = err?.code === 'ECONNABORTED' || String(err?.message || '').toLowerCase().includes('timeout');
      // Keep currently rendered emails on transient timeout to avoid empty-state flicker.
      if (!timedOut) {
        setEmails([]);
      }
    } finally {
      setLoading(false);
    }
  };

  const categories = React.useMemo(() => {
    const set = new Set([
      'Important',
      'To-Do',
      'Work',
      'Personal',
      'Finance',
      'Travel',
      'Newsletter',
      'Spam',
      'Uncategorized',
    ]);
    for (const e of emails) {
      const c = e.ai_category || e.category;
      if (c) set.add(c);
    }
    return ['all', ...Array.from(set)];
  }, [emails]);

  const filteredEmails = emails.filter((email) => {
    const subject = (email.subject || '').toLowerCase();
    const sender = (email.sender || '').toLowerCase();
    const body = (email.body_text || email.body || '').toLowerCase();
    const term = searchTerm.toLowerCase();
    const matchesSearch =
      !term || subject.includes(term) || sender.includes(term) || body.includes(term);
    const cat = email.ai_category || email.category || 'Uncategorized';
    const matchesCategory = filterCategory === 'all' || cat === filterCategory;
    return matchesSearch && matchesCategory;
  });

  const sortedEmails = [...filteredEmails].sort((a, b) => {
    if (sortBy === 'newest') {
      const pw = (p) => {
        const v = (p || '').toLowerCase();
        if (v === 'high') return 3;
        if (v === 'medium') return 2;
        if (v === 'low') return 1;
        return 0;
      };
      const d = pw(b.priority) - pw(a.priority);
      if (d !== 0) return d;
      return new Date(b.received_at || b.timestamp) - new Date(a.received_at || a.timestamp);
    }
    if (sortBy === 'oldest') {
      return new Date(a.received_at || a.timestamp) - new Date(b.received_at || b.timestamp);
    }
    if (sortBy === 'sender') return (a.sender || '').localeCompare(b.sender || '');
    return 0;
  });

  const groupedByCategory = React.useMemo(() => {
    const map = new Map();
    for (const e of sortedEmails) {
      const cat = e.ai_category || e.category || 'Uncategorized';
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat).push(e);
    }
    const order = [
      'Important',
      'To-Do',
      'Work',
      'Personal',
      'Finance',
      'Travel',
      'Newsletter',
      'Spam',
      'Uncategorized',
    ];
    const rest = [...map.keys()].filter((c) => !order.includes(c));
    const keys = [...order.filter((c) => map.has(c)), ...rest];
    return keys.map((k) => ({ category: k, emails: map.get(k) }));
  }, [sortedEmails]);

  const categoryStats = React.useMemo(() => {
    const s = { all: emails.length };
    for (const e of emails) {
      const c = e.ai_category || e.category || 'Uncategorized';
      s[c] = (s[c] || 0) + 1;
    }
    return s;
  }, [emails]);

  const formatDate = (d) => formatEmailDateLocal(d);

  const getPriorityIcon = (p) => {
    const v = (p || '').toLowerCase();
    if (v === 'high') return <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />;
    if (v === 'medium') return <Clock className="h-4 w-4 text-amber-600 flex-shrink-0" />;
    if (v === 'low') return <CheckCircle className="h-4 w-4 text-emerald-600 flex-shrink-0" />;
    return <Mail className="h-4 w-4 text-slate-400 flex-shrink-0" />;
  };

  const badgeClass = (cat) => {
    if (cat === 'Important') return 'badge-important';
    if (cat === 'To-Do') return 'badge-todo';
    if (cat === 'Newsletter') return 'badge-newsletter';
    return 'badge-default';
  };

  const openEmail = (email) => {
    setSelectedEmail(email);
    setView('detail');
  };

  const backToList = () => {
    setView('list');
    setSelectedEmail(null);
  };

  if (view === 'detail' && selectedEmail) {
    const accountId =
      selectedEmail.account_id || selectedAccountId;
    return (
      <div className="h-full flex flex-col min-h-0">
        <EmailDetailPage
          email={selectedEmail}
          accountId={accountId}
          onBack={backToList}
        />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* Credit Warning Banner */}
      {creditWarning && (
        <CreditWarningBanner
          creditsUsed={creditsUsed}
          creditsLimit={planLimits.aiCredits}
          onUpgradeClick={() => navigate('/billing/upgrade?plan=plus')}
        />
      )}

      {/* Premium Prompt Modal */}
      <PremiumPrompt
        isOpen={showPremiumPrompt}
        onClose={closePremiumPrompt}
        limitType={promptType}
        currentUsage={creditsUsed}
        monthlyLimit={planLimits.aiCredits}
      />

      <div className="flex flex-wrap justify-between items-center gap-4 mb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Inbox</h1>
          <p className="text-sm text-slate-600">Manage and process your emails with AI</p>
        </div>
        <div className="flex items-center gap-2">
          {emailAccounts.length > 0 && (
            <select
              value={selectedAccountId || ''}
              onChange={(e) => {
                const id = e.target.value;
                setSelectedAccountId(id);
                loadInbox(id);
              }}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              {emailAccounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.email}
                </option>
              ))}
            </select>
          )}
          <button
            type="button"
            onClick={() => selectedAccountId && loadInbox(selectedAccountId)}
            disabled={loading || !selectedAccountId}
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          {!isSuperAdmin && (
            <button
              type="button"
              onClick={() => navigate('/billing/upgrade')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg text-sm font-medium hover:from-indigo-700 hover:to-purple-700 transition-all transform hover:scale-105"
            >
              ⭐ Upgrade
            </button>
          )}
        </div>
      </div>

      <div className="mb-4 space-y-3">
        <div className="flex flex-wrap gap-2 overflow-x-auto pb-1">
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setFilterCategory(cat)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium whitespace-nowrap transition-colors ${
                filterCategory === cat
                  ? 'bg-indigo-600 border-indigo-600 text-white'
                  : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <span className="capitalize">{cat}</span>
              <span
                className={`px-1.5 py-0.5 rounded text-xs ${
                  filterCategory === cat ? 'bg-white/20' : 'bg-slate-100 text-slate-600'
                }`}
              >
                {categoryStats[cat] ?? 0}
              </span>
            </button>
          ))}
        </div>
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search emails..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-slate-900 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 border border-slate-300 rounded-lg text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="sender">By sender</option>
          </select>
          <button
            type="button"
            onClick={() => setViewMode((v) => (v === 'list' ? 'grouped' : 'list'))}
            className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
              viewMode === 'grouped'
                ? 'bg-indigo-600 border-indigo-600 text-white'
                : 'border-slate-300 text-slate-700 bg-white hover:bg-slate-50'
            }`}
          >
            {viewMode === 'grouped' ? 'List view' : 'Group by category'}
          </button>
        </div>
      </div>

      {viewMode === 'grouped' && groupedByCategory.length > 0 && (
        <div className="mb-4 p-3 rounded-lg border border-indigo-200 bg-indigo-50">
          <p className="text-sm font-medium text-indigo-900 mb-1">What this means</p>
          <p className="text-sm text-indigo-700">
            Emails are grouped by type. {groupedByCategory
              .map(({ category, emails: es }) => `${es.length} ${category}`)
              .join(' · ')}
          </p>
        </div>
      )}

      <div className="mb-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
        Each row shows sender, subject preview, and message time in your local timezone ({userTimeZone}).
      </div>

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
                    const cat = email.ai_category || email.category || 'Uncategorized';
                    const preview = (email.body_text || email.body || '').trim().slice(0, 80);
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
                          {!email.is_read && (
                            <div className="w-2 h-2 rounded-full bg-blue-500" />
                          )}
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
                    );
                  })}
                </div>
              ))}
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {sortedEmails.map((email) => {
                const cat = email.ai_category || email.category || 'Uncategorized';
                const preview = (email.body_text || email.body || '').trim().slice(0, 80);
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
                      {!email.is_read && (
                        <div className="w-2 h-2 rounded-full bg-blue-500" />
                      )}
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
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Inbox;
