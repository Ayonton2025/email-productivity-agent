import React, { useState, useEffect } from 'react';
import { Loader2, AlertCircle, FileIcon } from 'lucide-react';
import AttachmentCard from './AttachmentCard';
import attachmentService from '../../services/attachmentService';

/**
 * AttachmentsSection - Full attachments section for email detail view
 * Displays all attachments with metadata, analysis status, and analysis results
 */
const AttachmentsSection = ({ emailId, attachments: initialAttachments = [] }) => {
  const [attachments, setAttachments] = useState(initialAttachments);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analyzingAll, setAnalyzingAll] = useState(false);

  // Fetch attachments with analysis status
  useEffect(() => {
    if (emailId) {
      fetchAttachments();
    }
  }, [emailId]);

  const fetchAttachments = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await attachmentService.getEmailAttachments(emailId, true);
      if (result.success) {
        setAttachments(result.data.attachments || []);
      } else {
        setError('Could not load attachments');
      }
    } catch (err) {
      setError('Failed to load attachments');
      console.error('Fetch attachments error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeAll = async () => {
    setAnalyzingAll(true);
    setError(null);
    try {
      const result = await attachmentService.analyzeEmailAttachments(emailId);
      if (result.success) {
        // Refresh attachments to show analysis status
        setTimeout(() => {
          fetchAttachments();
        }, 2000);
      }
    } catch (err) {
      setError('Failed to trigger batch analysis');
      console.error('Batch analysis error:', err);
    } finally {
      setAnalyzingAll(false);
    }
  };

  const handleAnalysisComplete = async () => {
    // Refresh attachments when analysis completes
    await fetchAttachments();
  };

  if (!emailId) return null;

  // Empty state
  if (loading) {
    return (
      <div className="border-t px-6 py-8 bg-gray-50">
        <div className="flex items-center justify-center">
          <Loader2 className="h-5 w-5 text-gray-400 animate-spin mr-2" />
          <p className="text-sm text-gray-600">Loading attachments...</p>
        </div>
      </div>
    );
  }

  if (attachments.length === 0) {
    return (
      <div className="border-t px-6 py-8 bg-gray-50">
        <div className="text-center">
          <FileIcon className="mx-auto h-8 w-8 text-gray-400 mb-2" />
          <p className="text-sm font-medium text-gray-900">No attachments</p>
          <p className="text-xs text-gray-500 mt-1">This email has no attachments</p>
        </div>
      </div>
    );
  }

  // Count analyzed attachments
  const analyzedCount = attachments.filter(
    att => att.analysis?.status === 'completed'
  ).length;

  return (
    <div className="border-t bg-gray-50">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">
              Attachments
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              {attachments.length} {attachments.length === 1 ? 'file' : 'files'}
              {analyzedCount > 0 && ` • ${analyzedCount} analyzed`}
            </p>
          </div>

          {/* Batch analyze button */}
          {attachments.some(att => att.analysis?.status !== 'completed') && (
            <button
              onClick={handleAnalyzeAll}
              disabled={analyzingAll}
              className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {analyzingAll ? (
                <>
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>Analyzing All...</span>
                </>
              ) : (
                <span>📊 Analyze All</span>
              )}
            </button>
          )}
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded flex items-start space-x-2">
            <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-700">{error}</p>
          </div>
        )}
      </div>

      {/* Attachments list */}
      <div className="p-4 space-y-3">
        {attachments.map((attachment) => (
          <AttachmentCard
            key={attachment.id}
            attachment={attachment}
            emailId={emailId}
            onAnalysisComplete={handleAnalysisComplete}
          />
        ))}
      </div>

      {/* Info message about analysis */}
      <div className="px-6 py-3 bg-white border-t border-gray-100 text-xs text-gray-600">
        <p>
          💡 <span className="font-medium">Tip:</span> Analyze documents to get AI summaries, key points, entities, and sentiment analysis.
        </p>
      </div>
    </div>
  );
};

export default AttachmentsSection;
