import React, { useState } from 'react';
import { FileText, Download, Loader2, AlertCircle, CheckCircle } from 'lucide-react';
import attachmentService from '../../services/attachmentService';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

/**
 * AttachmentCard - Individual attachment card with download and analysis trigger
 * Shows file metadata and analysis status
 */
const AttachmentCard = ({ attachment, emailId, onAnalysisComplete = () => {} }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isSuperAdmin = Boolean(user?.is_super_admin || user?.is_admin || user?.is_superuser);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [showAnalysis, setShowAnalysis] = useState(false);

  // Handler for download button
  const handleDownload = async () => {
    setDownloading(true);
    setError(null);
    try {
      await attachmentService.downloadAttachmentFile(
        attachment.id,
        attachment.filename
      );
    } catch (err) {
      setError('Download failed');
      console.error('Download error:', err);
    } finally {
      setDownloading(false);
    }
  };

  // Handler for analyze button
  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      // Trigger analysis
      const result = await attachmentService.triggerAttachmentAnalysis(attachment.id);
      
      if (result.success) {
        // Analysis triggered successfully
        // Now fetch the analysis (may not be complete immediately)
        setTimeout(() => {
          fetchAnalysis();
        }, 1000);
      } else {
        setLoading(false);
      }
    } catch (err) {
      setError('Failed to trigger analysis');
      console.error('Analysis trigger error:', err);
      setLoading(false);
    }
  };

  // Fetch analysis results
  const fetchAnalysis = async () => {
    try {
      const result = await attachmentService.getAttachmentAnalysis(attachment.id);
      if (result.success) {
        const analysisData = result.data || {};
        if (analysisData.status === 'not_analyzed') {
          setError('Analysis not yet available. Please try again in a moment.');
          setLoading(false);
          return;
        }
        setAnalysis(analysisData);
        setShowAnalysis(true);
        onAnalysisComplete(analysisData);
      } else if (result.data?.status === 'not_analyzed') {
        // Analysis not yet available
        setError('Analysis not yet available. Please try again in a moment.');
        setLoading(false);
      }
    } catch (err) {
      setError('Could not fetch analysis results');
      console.error('Fetch analysis error:', err);
      setLoading(false);
    }
    setLoading(false);
  };

  const fileSize = attachment.file_size ? attachmentService.formatFileSize(attachment.file_size) : 'Unknown';

  return (
    <div className="bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-all overflow-hidden">
      {/* Header with file info */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <FileText className="h-5 w-5 text-gray-400 mt-1 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">
                {attachment.filename}
              </p>
              <div className="flex items-center space-x-2 mt-1 text-xs text-gray-500">
                <span>{attachment.extension?.toUpperCase() || 'File'}</span>
                <span>•</span>
                <span>{fileSize}</span>
                {attachment.created_at && (
                  <>
                    <span>•</span>
                    <span>{new Date(attachment.created_at).toLocaleDateString()}</span>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Status indicator */}
          <div className="ml-2">
            {attachment.analysis?.status === 'completed' && (
              <CheckCircle className="h-5 w-5 text-green-500" title="Analysis complete" />
            )}
            {loading && (
              <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
            )}
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded flex items-start space-x-2">
            <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-red-700">{error}</p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center space-x-2 mt-3">
          <button
            onClick={handleDownload}
            disabled={downloading || loading}
            className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 rounded hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {downloading ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Downloading...</span>
              </>
            ) : (
              <>
                <Download className="h-3 w-3" />
                <span>Download</span>
              </>
            )}
          </button>

          <button
            onClick={
              analysis
                ? () => setShowAnalysis(!showAnalysis)
                : (attachment.analysis?.status === 'completed' ? fetchAnalysis : handleAnalyze)
            }
            disabled={loading && !analysis}
            className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 rounded hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading && !analysis ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin" />
                <span>Analyzing...</span>
              </>
            ) : analysis ? (
              <span>{showAnalysis ? 'Hide Analysis' : 'Show Analysis'}</span>
            ) : (
              <span>Analyze</span>
            )}
          </button>
        </div>
      </div>

      {/* Analysis results section */}
      {analysis && showAnalysis && (
        <AnalysisDisplay
          analysis={analysis}
          filename={attachment.filename}
          isSuperAdmin={isSuperAdmin}
          onUpgrade={() => navigate('/billing/upgrade')}
        />
      )}
    </div>
  );
};

/**
 * AnalysisDisplay - Shows AI analysis results with tiering
 */
const AnalysisDisplay = ({ analysis, filename, onUpgrade, isSuperAdmin = false }) => {
  // Check if user is free tier (metadata only)
  const isFreeUser = !isSuperAdmin && !analysis.summary && !analysis.key_points && !!analysis.upgrade_message;

  if (isFreeUser) {
    return (
      <div className="border-t border-gray-200 bg-gradient-to-r from-amber-50 to-orange-50 p-4">
        <div className="flex items-start space-x-3">
          <div className="text-2xl">🎁</div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900">
              Unlock AI Analysis
            </p>
            <p className="text-xs text-gray-600 mt-1">
              {analysis.file_name
                ? `You received a document: ${analysis.file_name}${analysis.extracted_title ? ` (title: ${analysis.extracted_title})` : ''}.`
                : 'You received a document attachment.'}
            </p>
            <p className="text-xs text-gray-600 mt-1">
              {analysis.upgrade_message || 'Upgrade to Pro to see document summary, key points, entities, sentiment analysis, and more.'}
            </p>
            <button
              className="mt-2 text-xs font-medium text-amber-700 hover:text-amber-800 underline"
              onClick={onUpgrade}
            >
              View Pro Features
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Full analysis display for paid users
  return (
    <div className="border-t border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 p-4 space-y-3">
      {/* Summary */}
      {analysis.summary && (
        <div>
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1">
            Summary
          </h4>
          <p className="text-sm text-gray-700 line-clamp-3">
            {analysis.summary}
          </p>
        </div>
      )}

      {/* Key Points */}
      {analysis.key_points && analysis.key_points.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1">
            Key Points
          </h4>
          <ul className="space-y-1">
            {analysis.key_points.slice(0, 3).map((point, idx) => (
              <li key={idx} className="text-xs text-gray-700 flex items-start">
                <span className="mr-2">•</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Entities */}
      {analysis.entities && analysis.entities.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1">
            Entities
          </h4>
          <div className="flex flex-wrap gap-1">
            {analysis.entities.slice(0, 5).map((entity, idx) => (
              <span
                key={idx}
                className="inline-block px-2 py-0.5 text-xs bg-white text-gray-700 rounded border border-gray-200"
              >
                {entity}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Metadata */}
      {(analysis.sentiment || analysis.document_type || analysis.confidence_score) && (
        <div className="flex flex-wrap gap-3">
          {analysis.sentiment && (
            <div className="text-xs">
              <span className="text-gray-600">Sentiment: </span>
              <span className="font-medium text-gray-900 capitalize">
                {analysis.sentiment}
              </span>
            </div>
          )}
          {analysis.document_type && (
            <div className="text-xs">
              <span className="text-gray-600">Type: </span>
              <span className="font-medium text-gray-900 capitalize">
                {analysis.document_type}
              </span>
            </div>
          )}
          {analysis.confidence_score !== undefined && analysis.confidence_score !== null && (
            <div className="text-xs">
              <span className="text-gray-600">Confidence: </span>
              <span className="font-medium text-gray-900">
                {analysis.confidence_score > 1 ? `${analysis.confidence_score.toFixed(0)}%` : `${(analysis.confidence_score * 100).toFixed(0)}%`}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AttachmentCard;
