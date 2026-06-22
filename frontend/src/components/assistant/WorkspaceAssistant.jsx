import React, { useMemo, useState } from 'react';
import { Bot, Sparkles, Send, X } from 'lucide-react';
import { aiApi } from '../../services/api';

const QUICK_PROMPTS = {
  campaigns: [
    'Create a 3-step cold outreach campaign for B2B SaaS founders',
    'Build a follow-up campaign for users who opened but did not reply'
  ],
  workflows: [
    'Create a workflow that tags invoice emails and drafts a response',
    'Build a workflow for urgent VIP sender emails with approval'
  ],
  agents: [
    'Create a support agent for billing emails with strict approval',
    'Create a sales agent that tracks demos and drafts follow-ups'
  ],
  prompts: [
    'Generate a concise reply_draft prompt for enterprise clients',
    'Create an action_extraction prompt for deadline-heavy emails'
  ],
  default: [
    'Summarize what I should do next on this page',
    'Give me a simple setup plan for this section'
  ]
};

const WorkspaceAssistant = ({ page = 'default' }) => {
  const [open, setOpen] = useState(false);
  const [objective, setObjective] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('draft');
  const [confirming, setConfirming] = useState(false);
  const [pendingExecution, setPendingExecution] = useState(null);

  const suggestions = useMemo(() => {
    return QUICK_PROMPTS[page] || QUICK_PROMPTS.default;
  }, [page]);

  const runAssist = async (text) => {
    if (!text?.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await aiApi.assistWorkspace({
        page,
        objective: text.trim(),
        mode
      });
      const payload = res.data || null;
      setResponse(payload);
      if (
        payload?.requires_confirmation &&
        payload?.confirmation_token &&
        typeof payload?.draft === 'object' &&
        payload?.draft !== null
      ) {
        setPendingExecution({
          page,
          objective: text.trim(),
          confirmation_token: payload.confirmation_token,
          draft: payload.draft
        });
      } else if (!payload?.requires_confirmation) {
        setPendingExecution(null);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Assistant failed to respond.';
      setError(detail);
      setResponse(null);
      setPendingExecution(null);
    } finally {
      setLoading(false);
    }
  };

  const confirmExecute = async () => {
    const fallbackExecution = (
      response?.requires_confirmation &&
      response?.confirmation_token &&
      typeof response?.draft === 'object' &&
      response?.draft !== null
    )
      ? {
          page,
          objective: objective.trim(),
          confirmation_token: response.confirmation_token,
          draft: response.draft
        }
      : null;

    let executionToConfirm = pendingExecution || fallbackExecution;

    if (
      !executionToConfirm?.confirmation_token ||
      !executionToConfirm?.draft ||
      !executionToConfirm?.objective
    ) {
      // Attempt to generate a preview automatically before confirming.
      setError('');
      setConfirming(true);
      try {
        const previewRes = await aiApi.assistWorkspace({
          page,
          objective: objective.trim(),
          mode: 'execute'
        });
        const preview = previewRes.data || null;
        setResponse(preview);
        if (
          preview &&
          preview.requires_confirmation &&
          preview.confirmation_token &&
          typeof preview.draft === 'object' &&
          preview.draft !== null
        ) {
          // set the executionToConfirm from the freshly received preview
          executionToConfirm = {
            page,
            objective: objective.trim(),
            confirmation_token: preview.confirmation_token,
            draft: preview.draft
          };
        } else {
          setError('Execution preview unavailable. Please run Execute Now first.');
          setConfirming(false);
          return;
        }
      } catch (err) {
        const detail = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Failed to generate execution preview.';
        setError(detail);
        setConfirming(false);
        return;
      }
      setConfirming(false);
    }
    setConfirming(true);
    setError('');
    try {
      const res = await aiApi.assistWorkspace({
        page: executionToConfirm.page || page,
        objective: executionToConfirm.objective,
        mode: 'execute',
        confirmed: true,
        confirmation_token: executionToConfirm.confirmation_token,
        draft: executionToConfirm.draft
      });
      setResponse(res.data || null);
      setPendingExecution(null);
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Execution confirmation failed.';
      setError(detail);
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="fixed bottom-5 right-5 z-40">
      {open ? (
        <div className="w-[360px] max-w-[92vw] rounded-2xl border border-slate-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-indigo-100 p-2">
                <Bot className="h-4 w-4 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">Workplace</p>
                <p className="text-xs text-slate-500">Page: {page}</p>
              </div>
            </div>
            <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-600">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="space-y-3 p-4">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setMode('draft')}
                className={`rounded-full px-3 py-1 text-xs ${mode === 'draft' ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-700'}`}
              >
                Draft
              </button>
              <button
                onClick={() => setMode('execute')}
                className={`rounded-full px-3 py-1 text-xs ${mode === 'execute' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-700'}`}
              >
                Execute Now
              </button>
            </div>

            <div className="flex flex-wrap gap-2">
              {suggestions.map((item) => (
                <button
                  key={item}
                  onClick={() => {
                    setObjective(item);
                    runAssist(item);
                  }}
                  className="rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs text-indigo-700 hover:bg-indigo-100"
                >
                  {item}
                </button>
              ))}
            </div>

            <textarea
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="Tell Workplace what you want done..."
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              rows={3}
            />

            <button
              onClick={() => runAssist(objective)}
              disabled={loading || !objective.trim()}
              className={`inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-50 ${
                mode === 'execute' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-indigo-600 hover:bg-indigo-700'
              }`}
            >
              {loading ? <Sparkles className="h-4 w-4 animate-pulse" /> : <Send className="h-4 w-4" />}
              {loading ? (mode === 'execute' ? 'Executing...' : 'Thinking...') : (mode === 'execute' ? 'Execute Now' : 'Run Assistant')}
            </button>

            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 space-y-1">
                <div>{error}</div>
                {String(error).includes('No LLM providers configured') && (
                  <a href="/admin/super" className="inline-block rounded bg-red-600 px-2 py-1 font-semibold text-white hover:bg-red-700">
                    Configure LLM Providers
                  </a>
                )}
              </div>
            )}

            {response && (
              <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
                <p className="text-sm font-medium text-slate-900">{response.assistant_message || 'Done.'}</p>
                <p className="text-[11px] text-slate-500">
                  Provider: {response.provider || 'n/a'} | Model: {response.model || 'n/a'}
                </p>
                {Array.isArray(response.suggested_actions) && response.suggested_actions.length > 0 && (
                  <ul className="list-disc space-y-1 pl-4 text-xs text-slate-600">
                    {response.suggested_actions.slice(0, 4).map((action) => (
                      <li key={action}>{action}</li>
                    ))}
                  </ul>
                )}
                {response.execution?.created && (
                  <div className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-2 text-xs text-emerald-800">
                    <p className="font-semibold">Executed successfully</p>
                    <pre className="mt-1 whitespace-pre-wrap">{JSON.stringify(response.execution.created, null, 2)}</pre>
                  </div>
                )}
                {response.requires_confirmation && (
                  <div className="space-y-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-2 text-xs text-amber-900">
                    <p className="font-semibold">Approval Required</p>
                    <p>Review preview below and confirm to apply DB changes.</p>
                    <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-white p-2 text-[11px] text-slate-700">
{JSON.stringify(response.draft || {}, null, 2)}
                    </pre>
                    <div className="flex gap-2">
                      <button
                        onClick={confirmExecute}
                        disabled={confirming}
                        className="rounded bg-emerald-600 px-2 py-1 text-white hover:bg-emerald-700 disabled:opacity-50"
                      >
                        {confirming ? 'Confirming...' : 'Confirm Execute'}
                      </button>
                      <button
                        onClick={() => {
                          setResponse(null);
                          setPendingExecution(null);
                        }}
                        className="rounded bg-slate-200 px-2 py-1 text-slate-700 hover:bg-slate-300"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-indigo-700"
        >
          <Bot className="h-4 w-4" />
          Workplace
        </button>
      )}
    </div>
  );
};

export default WorkspaceAssistant;
