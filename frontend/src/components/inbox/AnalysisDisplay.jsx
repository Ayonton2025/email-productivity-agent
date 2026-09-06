const isMetadataOnly = (analysis, isSuperAdmin) =>
  !isSuperAdmin && !analysis.summary && !analysis.key_points && !!analysis.upgrade_message
import React from 'react'
const AnalysisDisplay = ({ analysis, onUpgrade, isSuperAdmin = false }) => {
  // Check if user is free tier (metadata only)
  const isFreeUser = isMetadataOnly(analysis, isSuperAdmin)

  if (isFreeUser) {
    return (
      <div className="border-t border-gray-200 bg-gradient-to-r from-amber-50 to-orange-50 p-4">
        <div className="flex items-start space-x-3">
          <div className="text-2xl">🎁</div>
          <div className="flex-1">
            <p className="text-sm font-medium text-gray-900">Unlock AI Analysis</p>
            <p className="text-xs text-gray-600 mt-1">
              {analysis.file_name
                ? `You received a document: ${analysis.file_name}${analysis.extracted_title ? ` (title: ${analysis.extracted_title})` : ''}.`
                : 'You received a document attachment.'}
            </p>
            <p className="text-xs text-gray-600 mt-1">
              {analysis.upgrade_message ||
                'Upgrade to Pro to see document summary, key points, entities, sentiment analysis, and more.'}
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
    )
  }

  // Full analysis display for paid users
  return (
    <div className="border-t border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50 p-4 space-y-3">
      {/* Summary */}
      {analysis.summary && (
        <div>
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1">Summary</h4>
          <p className="text-sm text-gray-700 line-clamp-3">{analysis.summary}</p>
        </div>
      )}

      {/* Key Points */}
      {analysis.key_points && analysis.key_points.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1">Key Points</h4>
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
          <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-1">Entities</h4>
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
              <span className="font-medium text-gray-900 capitalize">{analysis.sentiment}</span>
            </div>
          )}
          {analysis.document_type && (
            <div className="text-xs">
              <span className="text-gray-600">Type: </span>
              <span className="font-medium text-gray-900 capitalize">{analysis.document_type}</span>
            </div>
          )}
          {analysis.confidence_score !== undefined && analysis.confidence_score !== null && (
            <div className="text-xs">
              <span className="text-gray-600">Confidence: </span>
              <span className="font-medium text-gray-900">
                {analysis.confidence_score > 1
                  ? `${analysis.confidence_score.toFixed(0)}%`
                  : `${(analysis.confidence_score * 100).toFixed(0)}%`}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
export default AnalysisDisplay
