import AnalysisDisplay from './AnalysisDisplay'

import React from 'react'
import { FileText, Download, Loader2, AlertCircle, CheckCircle } from 'lucide-react'

export default function AttachmentCardView({
  attachment,
  fileSize,
  loading,
  error,
  handleDownload,
  downloading,
  analysis,
  setShowAnalysis,
  showAnalysis,
  fetchAnalysis,
  handleAnalyze,
  isSuperAdmin,
  navigate,
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 hover:border-gray-300 transition-all overflow-hidden">
      {/* Header with file info */}
      <div className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <FileText className="h-5 w-5 text-gray-400 mt-1 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate">{attachment.filename}</p>
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
            {loading && <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />}
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
                : attachment.analysis?.status === 'completed'
                  ? fetchAnalysis
                  : handleAnalyze
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
  )
}
