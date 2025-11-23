import React, { useState, useContext } from 'react';
import { useEmail } from '../../context/EmailContext';
import { agentApi } from '../../services/api';
import { 
  Star, Archive, Reply, Clock, Tag, User, Calendar,
  Play, Loader 
} from 'lucide-react';

const EmailDetail = ({ email }) => {
  const { updateEmailCategory } = useEmail();
  const [processing, setProcessing] = useState(false);
  const [agentResult, setAgentResult] = useState(null);

  const handleCategoryChange = async (newCategory) => {
    try {
      await updateEmailCategory(email.id, newCategory);
    } catch (err) {
      console.error('Error updating category:', err);
    }
  };

  const processWithAgent = async (promptType) => {
    setProcessing(true);
    setAgentResult(null);
    try {
      const response = await agentApi.processEmail({
      email_id: email.id,
      prompt_type: promptType
    });
      setAgentResult(response.data);
    } catch (err) {
      console.error('Error processing with agent:', err);
      setAgentResult({ error: 'Failed to process email' });
    } finally {
      setProcessing(false);
    }
  };

  const categories = ['Important', 'Newsletter', 'Spam', 'To-Do', 'Personal', 'Work'];

  return (
    <div className="h-full flex flex-col bg-white border border-gray-200 rounded-lg">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900">{email.subject}</h1>
            <div className="flex items-center mt-2 space-x-4">
              <div className="flex items-center text-sm text-gray-600">
                <User className="h-4 w-4 mr-1" />
                {email.sender}
              </div>
              <div className="flex items-center text-sm text-gray-600">
                <Calendar className="h-4 w-4 mr-1" />
                {new Date(email.timestamp).toLocaleString()}
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button className="p-2 text-gray-400 hover:text-yellow-500">
              <Star className="h-5 w-5" />
            </button>
            <button className="p-2 text-gray-400 hover:text-gray-600">
              <Archive className="h-5 w-5" />
            </button>
            <button className="p-2 text-gray-400 hover:text-blue-600">
              <Reply className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Category Selector */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Category
          </label>
          <div className="flex flex-wrap gap-2">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => handleCategoryChange(category)}
                className={`px-3 py-1 rounded-full text-xs font-medium ${
                  email.category === category
                    ? 'bg-indigo-100 text-indigo-800 border border-indigo-300'
                    : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                }`}
              >
                {category}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Agent Actions */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <h3 className="text-sm font-medium text-gray-700 mb-2">AI Actions</h3>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => processWithAgent('summary')}
            disabled={processing}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            {processing ? <Loader className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
            Summarize
          </button>
          <button
            onClick={() => processWithAgent('action_extraction')}
            disabled={processing}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            {processing ? <Loader className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
            Extract Tasks
          </button>
          <button
            onClick={() => processWithAgent('reply_draft')}
            disabled={processing}
            className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
          >
            {processing ? <Loader className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
            Draft Reply
          </button>
        </div>
      </div>

      {/* Agent Results */}
      {agentResult && (
        <div className="p-4 border-b border-gray-200 bg-blue-50">
          <h3 className="text-sm font-medium text-blue-900 mb-2">AI Result</h3>
          <div className="text-sm text-blue-800 bg-white p-3 rounded border">
            {agentResult.error ? (
              <p className="text-red-600">{agentResult.error}</p>
            ) : (
              <pre className="whitespace-pre-wrap">{agentResult.result}</pre>
            )}
          </div>
        </div>
      )}

      {/* Email Body */}
      <div className="flex-1 p-6 overflow-y-auto">
        <div className="prose max-w-none">
          <div className="whitespace-pre-wrap text-gray-900">{email.body}</div>
        </div>

        {/* Action Items */}
        {email.action_items && email.action_items.length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-3">Action Items</h3>
            <div className="space-y-2">
              {email.action_items.map((item, index) => (
                <div key={index} className="flex items-center p-3 bg-gray-50 rounded-lg">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{item.task}</p>
                    {item.deadline && (
                      <p className="text-sm text-gray-600">Deadline: {item.deadline}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        {email.summary && (
          <div className="mt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-3">Summary</h3>
            <p className="text-gray-700 bg-gray-50 p-4 rounded-lg">{email.summary}</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailDetail;