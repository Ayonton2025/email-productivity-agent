import React, { useContext } from 'react';
import { useEmail } from '../../context/EmailContext';
import { Download } from 'lucide-react';

const LoadMockInbox = () => {
  const { loadMockEmails, loading } = useEmail();

  return (
    <button
      onClick={loadMockEmails}
      disabled={loading}
      className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
    >
      <Download className="h-4 w-4 mr-2" />
      Load Mock Inbox
    </button>
  );
};

export default LoadMockInbox;