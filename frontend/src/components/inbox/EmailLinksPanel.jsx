import React from 'react'

import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'

import { shortenUrl } from '../../utils/emailParser.jsx'

export default function EmailLinksPanel({ emailLinks, expandLinks, setExpandLinks }) {
  return (
    emailLinks.length > 0 && (
      <div className="p-4 rounded-lg border border-slate-200 bg-slate-50">
        <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
          <ExternalLink className="h-4 w-4" />
          Links in this email ({emailLinks.length})
        </h3>
        <ul className="space-y-2">
          {/* Show first 2 links always */}
          {emailLinks.slice(0, 2).map((link, idx) => (
            <li
              key={idx}
              className="flex items-start gap-2 p-2 bg-white rounded border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all"
            >
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
          {expandLinks &&
            emailLinks.slice(2).map((link, idx) => (
              <li
                key={idx + 2}
                className="flex items-start gap-2 p-2 bg-white rounded border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all animate-fadeIn"
              >
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
    )
  )
}
