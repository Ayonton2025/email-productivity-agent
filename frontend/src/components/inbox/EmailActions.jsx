import { logger } from '../../utils/logger.js'
import React from 'react'

export default function EmailActions({ email }) {
  return (
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
            logger.debug('Toggle read status')
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
            logger.debug('Toggle flag')
          }}
        >
          {email.is_flagged ? '★ Flagged' : '☆ Flag'}
        </button>
      </div>
    </div>
  )
}
