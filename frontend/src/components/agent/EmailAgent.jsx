import React, { useState, useEffect, useRef, useContext } from 'react';
import { 
  Send, 
  Bot, 
  User, 
  RefreshCw, 
  Zap, 
  FileText, 
  Mail,
  Clock,
  Star,
  ThumbsUp,
  ThumbsDown,
  Copy,
  Download
} from 'lucide-react';
import { EmailContext } from '../../context/EmailContext';

const EmailAgent = () => {
  const { emails, selectedEmail, setSelectedEmail } = useContext(EmailContext);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState([]);
  const messagesEndRef = useRef(null);

  // Sample conversation starters
  const conversationStarters = [
    "Summarize my latest emails",
    "What urgent tasks do I have?",
    "Draft a reply to the most important email",
    "Show me emails from this week",
    "Categorize my unread emails"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize with welcome message
  useEffect(() => {
    setMessages([{
      id: 1,
      type: 'agent',
      content: "Hello! I'm your Email Productivity Agent. I can help you manage your inbox, summarize emails, extract tasks, and draft responses. How can I assist you today?",
      timestamp: new Date().toISOString()
    }]);
  }, []);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const responses = {
        "summarize": `I've analyzed your inbox. You have ${emails.length} emails with the following breakdown:
• ${emails.filter(e => e.category === 'Important').length} important emails
• ${emails.filter(e => e.category === 'To-Do').length} actionable items
• ${emails.filter(e => e.category === 'Newsletter').length} newsletters

The most urgent email is about the Q4 Project Review from ${emails[0]?.sender}.`,

        "tasks": `Here are your pending tasks:
${emails.filter(e => e.action_items && e.action_items.length > 0)
  .map(email => 
    email.action_items.map(item => 
      `• ${item.task} (Priority: ${item.priority || 'medium'})`
    ).join('\n')
  ).join('\n') || 'No specific tasks found in your emails.'}`,

        "draft": `I can help draft a reply! Please specify which email you'd like me to respond to, or use one of these options:
• "Draft reply to [sender name]"
• "Write professional response to meeting request"
• "Create casual reply to colleague"`,

        "default": `I understand you're asking about: "${inputMessage}". I can help you with:
• Email summarization and analysis
• Task extraction and prioritization
• Drafting professional responses
• Email categorization and organization
• Inbox management suggestions

What specific assistance would you like?`
      };

      let responseContent = responses.default;
      
      if (inputMessage.toLowerCase().includes('summarize')) {
        responseContent = responses.summarize;
      } else if (inputMessage.toLowerCase().includes('task')) {
        responseContent = responses.tasks;
      } else if (inputMessage.toLowerCase().includes('draft') || inputMessage.toLowerCase().includes('reply')) {
        responseContent = responses.draft;
      }

      const agentMessage = {
        id: Date.now() + 1,
        type: 'agent',
        content: responseContent,
        timestamp: new Date().toISOString(),
        suggestions: getResponseSuggestions(inputMessage)
      };

      setMessages(prev => [...prev, agentMessage]);
      setIsLoading(false);
    }, 1500);
  };

  const getResponseSuggestions = (userMessage) => {
    if (userMessage.toLowerCase().includes('summarize')) {
      return [
        "Show me only urgent emails",
        "What are my action items?",
        "Summarize emails from today"
      ];
    } else if (userMessage.toLowerCase().includes('task')) {
      return [
        "Show tasks with deadlines",
        "What's most urgent?",
        "Create a task list"
      ];
    }
    return [
      "Summarize my inbox",
      "What needs my attention?",
      "Draft a meeting response"
    ];
  };

  const handleQuickAction = (action) => {
    setInputMessage(action);
  };

  const handleSuggestionClick = (suggestion) => {
    setInputMessage(suggestion);
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
            <Bot className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Email Agent</h1>
            <p className="text-sm text-gray-600">Your AI-powered email assistant</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${isLoading ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}></div>
          <span className="text-sm text-gray-600">{isLoading ? 'Thinking...' : 'Online'}</span>
        </div>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row min-h-0">
        {/* Chat Container */}
        <div className="flex-1 flex flex-col">
          {/* Conversation Starters */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex flex-wrap gap-2">
              {conversationStarters.map((starter, index) => (
                <button
                  key={index}
                  onClick={() => handleQuickAction(starter)}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm transition-colors"
                >
                  {starter}
                </button>
              ))}
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 ${message.type === 'user' ? 'flex-row-reverse' : ''}`}
              >
                {/* Avatar */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                  message.type === 'user' 
                    ? 'bg-indigo-100 text-indigo-600' 
                    : 'bg-gradient-to-r from-indigo-500 to-purple-600 text-white'
                }`}>
                  {message.type === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                {/* Message Content */}
                <div className={`flex-1 max-w-3xl ${message.type === 'user' ? 'text-right' : ''}`}>
                  <div className={`inline-block rounded-2xl px-4 py-2 ${
                    message.type === 'user'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}>
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    
                    {/* Suggestions */}
                    {message.suggestions && message.type === 'agent' && (
                      <div className="mt-3 pt-3 border-t border-gray-200 border-opacity-30">
                        <div className="flex flex-wrap gap-2">
                          {message.suggestions.map((suggestion, idx) => (
                            <button
                              key={idx}
                              onClick={() => handleSuggestionClick(suggestion)}
                              className="px-2 py-1 bg-white bg-opacity-20 rounded-lg text-sm hover:bg-opacity-30 transition-colors"
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {/* Message Actions */}
                  <div className={`flex items-center gap-2 mt-1 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <span className="text-xs text-gray-500">
                      {formatTime(message.timestamp)}
                    </span>
                    {message.type === 'agent' && (
                      <div className="flex gap-1">
                        <button
                          onClick={() => copyToClipboard(message.content)}
                          className="p-1 text-gray-400 hover:text-gray-600 rounded"
                          title="Copy response"
                        >
                          <Copy className="h-3 w-3" />
                        </button>
                        <button className="p-1 text-gray-400 hover:text-green-600 rounded" title="Helpful">
                          <ThumbsUp className="h-3 w-3" />
                        </button>
                        <button className="p-1 text-gray-400 hover:text-red-600 rounded" title="Not helpful">
                          <ThumbsDown className="h-3 w-3" />
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {/* Loading Indicator */}
            {isLoading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-full flex items-center justify-center">
                  <Bot className="h-4 w-4 text-white" />
                </div>
                <div className="flex-1 max-w-3xl">
                  <div className="inline-block bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Ask me anything about your emails..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                disabled={isLoading}
              />
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <Send className="h-4 w-4" />
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Side Panel - Email Context */}
        <div className="lg:w-80 border-l border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">Email Context</h3>
            <p className="text-sm text-gray-600">Selected email for reference</p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4">
            {selectedEmail ? (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h4 className="font-semibold text-gray-900 truncate">
                      {selectedEmail.subject}
                    </h4>
                    <p className="text-sm text-gray-600">{selectedEmail.sender}</p>
                  </div>
                  <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                    selectedEmail.category === 'Important' ? 'bg-red-100 text-red-800' :
                    selectedEmail.category === 'To-Do' ? 'bg-green-100 text-green-800' :
                    selectedEmail.category === 'Newsletter' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {selectedEmail.category}
                  </span>
                </div>
                
                <p className="text-sm text-gray-700 line-clamp-4">
                  {selectedEmail.body}
                </p>
                
                {selectedEmail.action_items && selectedEmail.action_items.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <h5 className="text-xs font-semibold text-gray-900 mb-2">Action Items</h5>
                    <div className="space-y-1">
                      {selectedEmail.action_items.map((item, index) => (
                        <div key={index} className="flex items-center gap-2 text-xs">
                          <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full"></div>
                          <span className="text-gray-700">{item.task}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Mail className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p className="text-sm">No email selected</p>
                <p className="text-xs">Select an email from the inbox to use as context</p>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="p-4 border-t border-gray-200">
            <h4 className="font-semibold text-gray-900 mb-3">Quick Actions</h4>
            <div className="space-y-2">
              <button
                onClick={() => handleQuickAction("Summarize this email")}
                className="w-full flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
              >
                <FileText className="h-4 w-4 text-gray-600" />
                Summarize Email
              </button>
              <button
                onClick={() => handleQuickAction("Extract tasks from this email")}
                className="w-full flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
              >
                <Zap className="h-4 w-4 text-gray-600" />
                Extract Tasks
              </button>
              <button
                onClick={() => handleQuickAction("Draft a reply to this email")}
                className="w-full flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm"
              >
                <Send className="h-4 w-4 text-gray-600" />
                Draft Reply
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailAgent;