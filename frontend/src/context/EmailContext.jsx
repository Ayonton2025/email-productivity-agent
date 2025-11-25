import React, { createContext, useState, useContext, useEffect } from 'react';
import { emailApi } from '../services/api';
import { useAuth } from './AuthContext';

// Create and export the context
const EmailContext = createContext();

export const useEmail = () => {
  const context = useContext(EmailContext);
  if (!context) {
    throw new Error('useEmail must be used within an EmailProvider');
  }
  return context;
};

export const EmailProvider = ({ children }) => {
  const [emails, setEmails] = useState([]);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    category: 'all',
    search: '',
    sortBy: 'newest'
  });

  const { isAuthenticated, user } = useAuth();

  // Comprehensive Mock Inbox with 20 emails covering all required categories
  const mockEmails = [
    // Meeting Requests (4 emails)
    {
      id: '1',
      sender: 'project.manager@company.com',
      subject: 'Q4 Project Review Meeting',
      body: 'Hi team, We need to schedule the Q4 project review meeting for next week. Please review the attached project report and come prepared to discuss milestones, challenges, and next quarter planning. The meeting should take about 2 hours. Let me know your availability for Tuesday or Wednesday.',
      timestamp: '2024-01-08T10:30:00Z',
      category: 'Important',
      priority: 'high',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Review project report', deadline: '2024-01-12', priority: 'high' },
        { task: 'Prepare milestone updates', deadline: '2024-01-12', priority: 'medium' }
      ],
      summary: 'Meeting request for Q4 project review with attached report',
      metadata: { type: 'meeting_request', duration: '2 hours' }
    },
    {
      id: '2',
      sender: 'ceo@company.com',
      subject: 'Urgent: All-Hands Meeting Tomorrow',
      body: 'Team, We need to have an all-hands meeting tomorrow at 10 AM to discuss the recent market developments. This is mandatory for all department heads. Please clear your schedules.',
      timestamp: '2024-01-07T16:45:00Z',
      category: 'Important',
      priority: 'high',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Attend all-hands meeting', deadline: '2024-01-09', priority: 'high' }
      ],
      summary: 'Mandatory all-hands meeting about market developments',
      metadata: { type: 'meeting_request', mandatory: true }
    },
    {
      id: '3',
      sender: 'client.relations@external.com',
      subject: 'Project Kickoff Call - New Client',
      body: 'Hello! We would like to schedule a project kickoff call for our new client engagement. Available times: Monday 2-4 PM or Thursday 9-11 AM. Please confirm which slot works best for your team.',
      timestamp: '2024-01-07T14:20:00Z',
      category: 'To-Do',
      priority: 'medium',
      is_read: true,
      is_archived: false,
      action_items: [
        { task: 'Schedule project kickoff call', deadline: '2024-01-10', priority: 'medium' }
      ],
      summary: 'Request to schedule project kickoff call with new client',
      metadata: { type: 'meeting_request', client_related: true }
    },
    {
      id: '4',
      sender: 'hr.training@company.com',
      subject: 'Optional: New Software Training Session',
      body: 'We are offering optional training sessions for the new project management software. Sessions available: Jan 15th 10AM, Jan 16th 2PM, Jan 18th 11AM. RSVP required.',
      timestamp: '2024-01-06T11:15:00Z',
      category: 'Newsletter',
      priority: 'low',
      is_read: true,
      is_archived: false,
      action_items: [
        { task: 'RSVP for training if interested', deadline: '2024-01-12', priority: 'low' }
      ],
      summary: 'Optional training sessions for new software',
      metadata: { type: 'meeting_request', optional: true }
    },

    // Newsletters (4 emails)
    {
      id: '5',
      sender: 'newsletter@techdaily.com',
      subject: 'Tech Daily: AI Trends in 2024',
      body: 'Welcome to this week\'s Tech Daily newsletter! Featured Articles: - The Rise of Multimodal AI Systems - Quantum Computing Breakthroughs - Sustainable Tech Innovations - Career Opportunities in AI. Read more at our website.',
      timestamp: '2024-01-08T08:15:00Z',
      category: 'Newsletter',
      priority: 'low',
      is_read: true,
      is_archived: false,
      action_items: [],
      summary: 'Weekly tech newsletter featuring AI trends and developments',
      metadata: { type: 'newsletter', frequency: 'weekly' }
    },
    {
      id: '6',
      sender: 'marketing@industryinsights.com',
      subject: 'Monthly Market Analysis Report',
      body: 'Your monthly market analysis report is ready. Key findings: - 15% growth in Q4 - Emerging competitors - Regulatory changes affecting industry - Recommended strategic adjustments. Download the full report here: [link]',
      timestamp: '2024-01-05T09:30:00Z',
      category: 'Newsletter',
      priority: 'low',
      is_read: true,
      is_archived: true,
      action_items: [],
      summary: 'Monthly market analysis with growth statistics and recommendations',
      metadata: { type: 'newsletter', frequency: 'monthly' }
    },
    {
      id: '7',
      sender: 'updates@developercommunity.org',
      subject: 'Dev Community Weekly Digest',
      body: 'This week in developer community: - New framework releases - Upcoming webinars - Job postings - Open source projects needing contributors. Check out our events calendar for more details.',
      timestamp: '2024-01-04T07:45:00Z',
      category: 'Newsletter',
      priority: 'low',
      is_read: false,
      is_archived: false,
      action_items: [],
      summary: 'Weekly digest for developer community updates',
      metadata: { type: 'newsletter', audience: 'developers' }
    },
    {
      id: '8',
      sender: 'notifications@companyblog.com',
      subject: 'Company Blog: Leadership Insights',
      body: 'New article published: "Leading Remote Teams Effectively" by our CEO. Learn about: - Communication best practices - Productivity metrics - Team building activities - Tools and technologies.',
      timestamp: '2024-01-03T13:20:00Z',
      category: 'Newsletter',
      priority: 'low',
      is_read: false,
      is_archived: false,
      action_items: [],
      summary: 'Company blog update with leadership article',
      metadata: { type: 'newsletter', source: 'company_blog' }
    },

    // Spam-like messages (3 emails)
    {
      id: '9',
      sender: 'winner@lotteryinternational.com',
      subject: 'CONGRATULATIONS! You Won $2,500,000',
      body: 'Dear Winner, You have been selected as the lucky winner of $2,500,000 in our international lottery! To claim your prize, please provide your bank details and pay a small processing fee of $500. Contact us immediately!',
      timestamp: '2024-01-08T02:15:00Z',
      category: 'Spam',
      priority: 'low',
      is_read: false,
      is_archived: false,
      action_items: [],
      summary: 'Suspicious lottery winning notification requesting bank details',
      metadata: { type: 'spam', risk: 'high' }
    },
    {
      id: '10',
      sender: 'security@bank-update.com',
      subject: 'URGENT: Your Account Will Be Suspended',
      body: 'We detected suspicious activity on your bank account. Click here to verify your identity immediately or your account will be suspended within 24 hours. [suspicious-link]',
      timestamp: '2024-01-07T23:30:00Z',
      category: 'Spam',
      priority: 'low',
      is_read: false,
      is_archived: true,
      action_items: [],
      summary: 'Phishing email pretending to be from bank with suspicious link',
      metadata: { type: 'spam', risk: 'high' }
    },
    {
      id: '11',
      sender: 'deals@shoppingdiscounts.net',
      subject: '90% OFF - Limited Time Offer!',
      body: 'HUGE DISCOUNTS! Everything 90% off for the next 2 hours only! Use code: MEGADEAL. Shop now before time runs out! [link-to-shop]',
      timestamp: '2024-01-06T18:45:00Z',
      category: 'Spam',
      priority: 'low',
      is_read: true,
      is_archived: false,
      action_items: [],
      summary: 'Aggressive marketing email with unrealistic discounts',
      metadata: { type: 'spam', risk: 'medium' }
    },

    // Task Requests (5 emails)
    {
      id: '12',
      sender: 'hr@company.com',
      subject: 'ACTION REQUIRED: Benefits Enrollment Deadline',
      body: 'Dear Employee, This is a reminder that the benefits enrollment period closes this Friday at 5 PM. You must complete your enrollment selection by this deadline. Visit the HR portal to make your selections.',
      timestamp: '2024-01-08T09:45:00Z',
      category: 'To-Do',
      priority: 'high',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Complete benefits enrollment', deadline: '2024-01-12', priority: 'high' }
      ],
      summary: 'Benefits enrollment reminder with Friday deadline',
      metadata: { type: 'task_request', action_required: true }
    },
    {
      id: '13',
      sender: 'it.support@company.com',
      subject: 'Password Update Required',
      body: 'Your password will expire in 7 days. Please update your password following our security policy: - Minimum 12 characters - Include special characters - No reuse of previous passwords. Update here: [company-portal]',
      timestamp: '2024-01-07T11:20:00Z',
      category: 'To-Do',
      priority: 'medium',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Update expired password', deadline: '2024-01-14', priority: 'medium' }
      ],
      summary: 'Password expiration notice requiring update within 7 days',
      metadata: { type: 'task_request', security_related: true }
    },
    {
      id: '14',
      sender: 'compliance@company.com',
      subject: 'Mandatory Training: Data Privacy',
      body: 'Complete the annual data privacy training by January 20th. This is mandatory for all employees. The training takes approximately 45 minutes and must be completed during work hours.',
      timestamp: '2024-01-06T15:10:00Z',
      category: 'To-Do',
      priority: 'medium',
      is_read: true,
      is_archived: false,
      action_items: [
        { task: 'Complete data privacy training', deadline: '2024-01-20', priority: 'medium' }
      ],
      summary: 'Mandatory data privacy training requirement',
      metadata: { type: 'task_request', mandatory: true }
    },
    {
      id: '15',
      sender: 'manager@department.com',
      subject: 'Weekly Status Report Due',
      body: 'Please submit your weekly status report by EOD Friday. Include: - Completed tasks - Next week priorities - Blockers or challenges - Resource needs.',
      timestamp: '2024-01-05T16:30:00Z',
      category: 'To-Do',
      priority: 'medium',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Submit weekly status report', deadline: '2024-01-12', priority: 'medium' }
      ],
      summary: 'Weekly status report submission reminder',
      metadata: { type: 'task_request', recurring: true }
    },
    {
      id: '16',
      sender: 'finance@company.com',
      subject: 'Expense Reports Q4 Submission',
      body: 'All Q4 expense reports must be submitted by January 15th for processing. Please ensure all receipts are attached and expenses are properly categorized according to company policy.',
      timestamp: '2024-01-04T10:15:00Z',
      category: 'To-Do',
      priority: 'medium',
      is_read: true,
      is_archived: false,
      action_items: [
        { task: 'Submit Q4 expense reports', deadline: '2024-01-15', priority: 'medium' }
      ],
      summary: 'Q4 expense report submission deadline reminder',
      metadata: { type: 'task_request', finance_related: true }
    },

    // Project Updates (4 emails)
    {
      id: '17',
      sender: 'project.updates@company.com',
      subject: 'Project Phoenix: Phase 2 Completed',
      body: 'Great news! Phase 2 of Project Phoenix has been completed ahead of schedule. Key achievements: - All milestones met - Budget maintained - Client satisfaction high. Phase 3 planning begins next week.',
      timestamp: '2024-01-08T13:45:00Z',
      category: 'Important',
      priority: 'medium',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Review Phase 2 completion report', deadline: '2024-01-15', priority: 'low' }
      ],
      summary: 'Project Phoenix Phase 2 completed successfully ahead of schedule',
      metadata: { type: 'project_update', status: 'completed' }
    },
    {
      id: '18',
      sender: 'team.lead@development.com',
      subject: 'Code Review: New Feature Implementation',
      body: 'The new authentication feature is ready for code review. Key changes: - OAuth2 implementation - Security enhancements - API updates. Please review the pull request by EOD tomorrow.',
      timestamp: '2024-01-07T14:50:00Z',
      category: 'To-Do',
      priority: 'medium',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Review authentication feature code', deadline: '2024-01-09', priority: 'medium' }
      ],
      summary: 'Code review request for new authentication feature',
      metadata: { type: 'project_update', technical: true }
    },
    {
      id: '19',
      sender: 'client@importantclient.com',
      subject: 'Feedback: Website Redesign',
      body: 'We have reviewed the website redesign mockups. Overall positive feedback with minor revisions requested: - Color scheme adjustments - Navigation improvements - Mobile optimization enhancements. Please schedule a call to discuss.',
      timestamp: '2024-01-06T12:25:00Z',
      category: 'Important',
      priority: 'medium',
      is_read: true,
      is_archived: false,
      action_items: [
        { task: 'Schedule call to discuss client feedback', deadline: '2024-01-10', priority: 'medium' }
      ],
      summary: 'Client feedback on website redesign with revision requests',
      metadata: { type: 'project_update', client_feedback: true }
    },
    {
      id: '20',
      sender: 'qa@company.com',
      subject: 'URGENT: Production Bug Found',
      body: 'Critical bug found in production: Users unable to complete checkout process. Error occurs during payment processing. Immediate fix required. Development team alerted. Status: Investigating root cause.',
      timestamp: '2024-01-05T08:05:00Z',
      category: 'Important',
      priority: 'high',
      is_read: false,
      is_archived: false,
      action_items: [
        { task: 'Fix production checkout bug', deadline: '2024-01-05', priority: 'high' }
      ],
      summary: 'Critical production bug affecting user checkout process',
      metadata: { type: 'project_update', critical: true }
    }
  ];

  // Load user's real emails when authenticated
  const loadEmails = async () => {
    if (!isAuthenticated) {
      setEmails(mockEmails);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await emailApi.getUserInbox(filters);
      setEmails(response.data);
    } catch (err) {
      console.error('Error loading emails:', err);
      setError('Failed to load emails');
      // Fallback to mock data for demo
      setEmails(mockEmails);
    } finally {
      setLoading(false);
    }
  };

  // Load mock emails for demo purposes
  const loadMockEmails = async () => {
    setLoading(true);
    setError(null);
    try {
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 500));
      setEmails(mockEmails);
    } catch (err) {
      setError('Failed to load mock emails');
    } finally {
      setLoading(false);
    }
  };

  // Sync real emails from connected accounts
  const syncUserEmails = async () => {
    if (!isAuthenticated) {
      setError('Please sign in to sync emails');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await emailApi.syncUserEmails();
      await loadEmails(); // Reload emails after sync
      return { success: true, data: response.data };
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to sync emails';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  const updateEmailCategory = async (emailId, category) => {
    try {
      if (isAuthenticated) {
        // Update via API for real emails
        await emailApi.updateEmailCategory(emailId, category);
      }
      
      // Update local state
      setEmails(prev => prev.map(email =>
        email.id === emailId ? { ...email, category } : email
      ));
      
      if (selectedEmail && selectedEmail.id === emailId) {
        setSelectedEmail(prev => ({ ...prev, category }));
      }
    } catch (err) {
      console.error('Error updating email category:', err);
      throw err;
    }
  };

  // Filter emails based on current filters
  const filteredEmails = emails.filter(email => {
    const matchesCategory = filters.category === 'all' || email.category === filters.category;
    const matchesSearch = 
      email.subject.toLowerCase().includes(filters.search.toLowerCase()) ||
      email.sender.toLowerCase().includes(filters.search.toLowerCase()) ||
      email.body.toLowerCase().includes(filters.search.toLowerCase());
    
    return matchesCategory && matchesSearch;
  });

  // Sort emails based on current sort
  const sortedEmails = [...filteredEmails].sort((a, b) => {
    if (filters.sortBy === 'newest') {
      return new Date(b.timestamp) - new Date(a.timestamp);
    } else if (filters.sortBy === 'oldest') {
      return new Date(a.timestamp) - new Date(b.timestamp);
    } else if (filters.sortBy === 'sender') {
      return a.sender.localeCompare(b.sender);
    }
    return 0;
  });

  // Load emails when component mounts or authentication changes
  useEffect(() => {
    if (isAuthenticated) {
      loadEmails();
    } else {
      setEmails(mockEmails);
    }
  }, [isAuthenticated]);

  // Reload emails when filters change
  useEffect(() => {
    if (isAuthenticated) {
      loadEmails();
    }
  }, [filters]);

  const value = {
    emails: sortedEmails,
    selectedEmail,
    setSelectedEmail,
    loading,
    error,
    filters,
    setFilters,
    loadEmails,
    loadMockEmails,
    syncUserEmails,
    updateEmailCategory,
    isUsingRealEmails: isAuthenticated,
    userEmail: user?.email,
  };

  return (
    <EmailContext.Provider value={value}>
      {children}
    </EmailContext.Provider>
  );
};

// Export the context for direct consumption
export { EmailContext };
