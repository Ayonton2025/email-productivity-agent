import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

// Import global styles
import './styles/globals.css'

/**
 * InboxAI - Advanced Email Productivity Agent
 * 
 * Enhanced with:
 * - Real email provider integration (Gmail, Outlook)
 * - User authentication & account management
 * - Advanced OpenAI API integration
 * - Production-ready error handling
 * - Performance monitoring for AI operations
 * - Multi-user support with data isolation
 */

// Enhanced Error Boundary with AI-specific error handling
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorType: 'general'
    };
  }

  static getDerivedStateFromError(error) {
    // Classify error types for better user messaging
    let errorType = 'general';
    
    if (error.message?.includes('NetworkError') || error.message?.includes('Failed to fetch')) {
      errorType = 'network';
    } else if (error.message?.includes('OpenAI') || error.message?.includes('API')) {
      errorType = 'ai_service';
    } else if (error.message?.includes('OAuth') || error.message?.includes('authentication')) {
      errorType = 'auth';
    } else if (error.message?.includes('Email provider') || error.message?.includes('Gmail') || error.message?.includes('Outlook')) {
      errorType = 'email_provider';
    }
    
    return { hasError: true, errorType };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    
    // Enhanced error logging with AI service context
    console.error('InboxAI Error Boundary caught an error:', {
      error: error.toString(),
      errorType: this.state.errorType,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent
    });
    
    // Send to error reporting service in production
    if (import.meta.env.PROD) {
      this.reportErrorToService(error, errorInfo);
    }
  }

  reportErrorToService(error, errorInfo) {
    // Implementation for error reporting service (Sentry, LogRocket, etc.)
    try {
      // Example: Send to analytics service
      if (window.gtag) {
        window.gtag('event', 'exception', {
          description: error.toString(),
          fatal: true,
          error_type: this.state.errorType
        });
      }
    } catch (reportingError) {
      console.warn('Error reporting failed:', reportingError);
    }
  }

  getErrorMessage() {
    const { errorType } = this.state;
    
    const messages = {
      network: {
        title: "Connection Issue",
        description: "We're having trouble connecting to our services. Please check your internet connection.",
        action: "Check Connection"
      },
      ai_service: {
        title: "AI Service Temporarily Unavailable",
        description: "Our AI features are currently experiencing issues. Basic email functions remain available.",
        action: "Retry AI Features"
      },
      auth: {
        title: "Authentication Error", 
        description: "There was an issue with your session. Please sign in again.",
        action: "Sign In Again"
      },
      email_provider: {
        title: "Email Provider Connection Issue",
        description: "There was an issue with your email provider connection. Please reconnect your account.",
        action: "Reconnect Account"
      },
      general: {
        title: "Something went wrong",
        description: "We're sorry, but the application encountered an unexpected error.",
        action: "Reload Application"
      }
    };
    
    return messages[errorType] || messages.general;
  }

  handleRecoveryAction = () => {
    const { errorType } = this.state;
    
    switch (errorType) {
      case 'auth':
        // Clear auth tokens and redirect to login
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
        break;
      case 'email_provider':
        // Redirect to email accounts page
        window.location.hash = '#email-accounts';
        this.setState({ hasError: false, error: null, errorInfo: null });
        break;
      default:
        window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      const errorMessage = this.getErrorMessage();
      
      return (
        <div className="min-h-screen bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center p-4 dark:from-red-900 dark:to-red-800">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center dark:bg-gray-800">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4 dark:bg-red-900">
              {this.state.errorType === 'network' ? (
                <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
                </svg>
              ) : this.state.errorType === 'ai_service' ? (
                <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              ) : this.state.errorType === 'auth' ? (
                <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              ) : (
                <svg className="w-8 h-8 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              )}
            </div>
            
            <h2 className="text-xl font-semibold text-gray-900 mb-2 dark:text-white">
              {errorMessage.title}
            </h2>
            <p className="text-gray-600 mb-4 dark:text-gray-300">
              {errorMessage.description}
            </p>
            
            {/* Enhanced error details for development */}
            {import.meta.env.DEV && this.state.error && (
              <details className="text-left bg-gray-50 rounded p-3 mb-4 text-sm dark:bg-gray-700">
                <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-300">
                  Error Details (Development)
                </summary>
                <div className="mt-2">
                  <p className="text-red-600 dark:text-red-400 font-mono text-xs">
                    {this.state.error.toString()}
                  </p>
                  <div className="text-xs text-gray-500 mt-1">
                    Type: {this.state.errorType}
                  </div>
                  <pre className="text-gray-600 dark:text-gray-400 text-xs mt-2 overflow-auto max-h-32">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </div>
              </details>
            )}
            
            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleRecoveryAction}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                {errorMessage.action}
              </button>
              
              {(this.state.errorType === 'email_provider' || this.state.errorType === 'auth') && (
                <button
                  onClick={() => {
                    // Navigate to appropriate page based on error type
                    const targetPage = this.state.errorType === 'email_provider' ? '#email-accounts' : '/login';
                    window.location.href = targetPage;
                    this.setState({ hasError: false, error: null, errorInfo: null });
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
                >
                  {this.state.errorType === 'email_provider' ? 'Go to Email Accounts' : 'Go to Sign In'}
                </button>
              )}
              
              <button
                onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 dark:bg-gray-600 dark:text-gray-300"
              >
                Try Again
              </button>
            </div>
            
            {/* Enhanced support information */}
            <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-600">
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                Need help? Here are some options:
              </p>
              <div className="flex justify-center gap-4 text-xs">
                <button 
                  onClick={() => window.open('https://github.com/your-username/inboxai/issues', '_blank')}
                  className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
                >
                  Report Issue
                </button>
                <button 
                  onClick={() => window.open('mailto:support@inboxai.example.com', '_blank')}
                  className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
                >
                  Contact Support
                </button>
                <button 
                  onClick={() => window.open('https://inboxai.example.com/docs', '_blank')}
                  className="text-indigo-600 hover:text-indigo-700 dark:text-indigo-400"
                >
                  Documentation
                </button>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Enhanced performance monitoring with AI operation tracking
const withPerformanceMonitoring = (WrappedComponent) => {
  return function PerformanceMonitoredApp(props) {
    const [performanceMetrics, setPerformanceMetrics] = React.useState({
      appLoadTime: null,
      aiOperationTimes: [],
      networkRequests: [],
      authOperations: []
    });

    React.useEffect(() => {
      // Measure initial app load time
      const startTime = performance.now();
      
      // Track API performance including auth and email operations
      const originalFetch = window.fetch;
      window.fetch = function(...args) {
        const start = performance.now();
        return originalFetch.apply(this, args).then(response => {
          const duration = performance.now() - start;
          const url = args[0];
          
          // Track different types of operations
          if (url?.includes('/api/auth/')) {
            setPerformanceMetrics(prev => ({
              ...prev,
              authOperations: [...prev.authOperations, {
                endpoint: url,
                duration: duration,
                timestamp: new Date().toISOString()
              }].slice(-10)
            }));
          } else if (url?.includes('/api/email-accounts/')) {
            setPerformanceMetrics(prev => ({
              ...prev,
              aiOperationTimes: [...prev.aiOperationTimes, {
                endpoint: url,
                duration: duration,
                type: 'email_provider',
                timestamp: new Date().toISOString()
              }].slice(-20)
            }));
          } else if (url?.includes('/api/') || url?.includes('openai')) {
            setPerformanceMetrics(prev => ({
              ...prev,
              aiOperationTimes: [...prev.aiOperationTimes, {
                endpoint: url,
                duration: duration,
                type: 'ai_service',
                timestamp: new Date().toISOString()
              }].slice(-20)
            }));
          }
          
          return response;
        });
      };
      
      return () => {
        const mountTime = performance.now() - startTime;
        window.fetch = originalFetch; // Restore original fetch
        
        setPerformanceMetrics(prev => ({
          ...prev,
          appLoadTime: mountTime
        }));
        
        if (import.meta.env.DEV) {
          console.log(`🚀 InboxAI mounted in ${mountTime.toFixed(2)}ms`);
          
          // Performance insights
          const aiOps = performanceMetrics.aiOperationTimes.length;
          const authOps = performanceMetrics.authOperations.length;
          
          console.log(`📊 Performance Summary:`);
          console.log(`   - AI Operations: ${aiOps}`);
          console.log(`   - Auth Operations: ${authOps}`);
          
          if (mountTime > 1000) {
            console.warn('⚠️  App mount time is high. Consider optimizing initial load.');
          }
        }
        
        // Log to analytics in production
        if (import.meta.env.PROD) {
          if (window.gtag) {
            window.gtag('event', 'app_load', {
              load_time: Math.round(mountTime),
              ai_operations: performanceMetrics.aiOperationTimes.length,
              auth_operations: performanceMetrics.authOperations.length
            });
          }
        }
      };
    }, []);

    // Monitor service health including auth and email providers
    React.useEffect(() => {
      const checkServiceHealth = async () => {
        try {
          // Check auth service
          const authResponse = await fetch('/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
            }
          });
          
          if (!authResponse.ok && authResponse.status !== 401) {
            console.warn('⚠️  Auth service health check failed');
          }

          // Check AI service health
          const aiResponse = await fetch('/api/v1/health/ai');
          if (!aiResponse.ok) {
            console.warn('⚠️  AI service health check failed');
          }
        } catch (error) {
          console.warn('⚠️  Service health check failed:', error);
        }
      };

      // Check service health every 5 minutes
      const healthCheckInterval = setInterval(checkServiceHealth, 5 * 60 * 1000);
      
      return () => clearInterval(healthCheckInterval);
    }, []);

    return <WrappedComponent {...props} />;
  };
};

// Enhanced App component with AI capabilities monitoring
const EnhancedApp = withPerformanceMonitoring(App);

// Enhanced Strict Mode wrapper with development tools
const StrictModeWrapper = ({ children }) => {
  const [showDevTools, setShowDevTools] = React.useState(false);
  
  // Development-only features
  if (import.meta.env.DEV) {
    // Add development tools
    React.useEffect(() => {
      const handleKeyPress = (event) => {
        // Ctrl+Shift+D to toggle dev tools
        if (event.ctrlKey && event.shiftKey && event.key === 'D') {
          setShowDevTools(prev => !prev);
        }
      };
      
      window.addEventListener('keydown', handleKeyPress);
      return () => window.removeEventListener('keydown', handleKeyPress);
    }, []);
    
    return (
      <React.StrictMode>
        {children}
        {showDevTools && <DevelopmentTools />}
      </React.StrictMode>
    );
  }
  
  return <React.StrictMode>{children}</React.StrictMode>;
};

// Enhanced Development tools component with auth and email provider info
const DevelopmentTools = () => {
  const [metrics, setMetrics] = React.useState({});
  const [authStatus, setAuthStatus] = React.useState('Checking...');
  
  React.useEffect(() => {
    // Check auth status
    const token = localStorage.getItem('auth_token');
    if (token) {
      setAuthStatus('Authenticated');
    } else {
      setAuthStatus('Not Authenticated');
    }

    // Simulate metrics collection
    const interval = setInterval(() => {
      setMetrics({
        memory: (performance.memory?.usedJSHeapSize / 1048576).toFixed(2) + ' MB',
        connections: 'Active',
        aiStatus: 'Connected'
      });
    }, 2000);
    
    return () => clearInterval(interval);
  }, []);
  
  return (
    <div className="fixed bottom-4 right-4 bg-gray-800 text-white p-4 rounded-lg shadow-lg text-xs z-50 max-w-xs">
      <div className="font-bold mb-2">🧠 InboxAI Dev Tools</div>
      <div className="space-y-1">
        <div>Memory: {metrics.memory}</div>
        <div>Auth: <span className={authStatus === 'Authenticated' ? 'text-green-400' : 'text-yellow-400'}>{authStatus}</span></div>
        <div>AI Status: {metrics.aiStatus}</div>
        <div className="text-green-400">✓ Real Email Integration Ready</div>
        <div className="text-green-400">✓ User Authentication System</div>
        <div className="text-green-400">✓ Multi-User Support</div>
        <div className="text-green-400">✓ OpenAI Enhanced</div>
      </div>
      <div className="flex gap-2 mt-2">
        <button
          onClick={() => {
            // Prefer production backend from environment variable
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            // Open /docs endpoint
            window.open(`${apiUrl}/docs`, '_blank');
          }}
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 px-2 py-1 rounded text-xs"
        >
          API Docs
        </button>
        <button 
          onClick={() => {
            localStorage.removeItem('auth_token');
            window.location.reload();
          }}
          className="flex-1 bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs"
        >
          Clear Auth
        </button>
      </div>
    </div>
  );
};

// Clean main render function without browser detection
const renderApp = () => {
  const rootElement = document.getElementById('root');
  
  if (!rootElement) {
    console.error('Root element not found!');
    
    // Create fallback UI
    document.body.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: system-ui;">
        <div style="text-align: center;">
          <div style="font-size: 2rem; margin-bottom: 1rem;">❌</div>
          <h1 style="font-size: 1.5rem; margin-bottom: 0.5rem;">InboxAI Failed to Load</h1>
          <p style="margin-bottom: 1rem;">Critical error: Root element missing</p>
          <button onclick="window.location.reload()" style="padding: 0.5rem 1rem; background: white; color: #6366f1; border: none; border-radius: 0.5rem; cursor: pointer;">
            Restart Application
          </button>
        </div>
      </div>
    `;
    return;
  }

  try {
    const root = ReactDOM.createRoot(rootElement);
    
    root.render(
      <StrictModeWrapper>
        <ErrorBoundary>
          <EnhancedApp />
        </ErrorBoundary>
      </StrictModeWrapper>
    );

    // Enhanced initialization logging with new features
    console.log(`
    🚀 InboxAI Initialized Successfully!
    
    New Features Available:
    ✅ User Authentication & Registration
    ✅ Email Verification System
    ✅ Password Reset Functionality
    ✅ Real Email Provider Integration (Gmail, Outlook)
    ✅ Multi-User Data Isolation
    ✅ Advanced OpenAI AI Processing
    ✅ Smart Email Categorization
    ✅ AI-Powered Draft Generation
    ✅ Cross-Email Insights
    ✅ Productivity Analytics
    
    Next Steps:
    1. Register or sign in to your account
    2. Connect your email provider in Email Accounts
    3. Configure OpenAI API for enhanced features
    4. Start managing real emails with AI assistance
    
    Need help? Check /docs for integration guides.
    `);
    
    // Enhanced loading indicator removal with smooth transition
    const loadingContainer = document.querySelector('.loading-container');
    if (loadingContainer) {
      // Add success message before removing
      const successMessage = document.createElement('div');
      successMessage.className = 'loading-success';
      successMessage.innerHTML = `
        <div style="text-align: center; color: white; margin-top: 1rem;">
          <div style="font-size: 2rem;">🎉</div>
          <div>InboxAI Ready!</div>
          <div style="font-size: 0.8rem; margin-top: 0.5rem; opacity: 0.8;">
            Now with User Authentication & Real Email Support
          </div>
        </div>
      `;
      loadingContainer.appendChild(successMessage);
      
      setTimeout(() => {
        loadingContainer.style.opacity = '0';
        loadingContainer.style.transform = 'scale(0.95)';
        loadingContainer.style.transition = 'all 0.5s ease';
        
        setTimeout(() => {
          if (loadingContainer.parentNode) {
            loadingContainer.parentNode.removeChild(loadingContainer);
          }
        }, 500);
      }, 1000);
    }

  } catch (error) {
    console.error('💥 Failed to initialize InboxAI:', error);
    
    // Enhanced error UI with specific guidance
    let errorGuidance = 'Please refresh the page and try again.';
    
    if (error.message?.includes('ReactDOM')) {
      errorGuidance = 'This might be a browser compatibility issue. Try updating your browser.';
    } else if (error.message?.includes('memory')) {
      errorGuidance = 'Your device is low on memory. Try closing other tabs and refresh.';
    } else if (error.message?.includes('auth')) {
      errorGuidance = 'Authentication system initialization failed. Please clear browser data and try again.';
    }
    
    rootElement.innerHTML = `
      <div class="loading-container" style="background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);">
        <div style="font-size: 3rem; margin-bottom: 1rem;">💥</div>
        <div class="loading-text" style="font-size: 1.5rem;">InboxAI Failed to Start</div>
        <div class="loading-subtext" style="margin-bottom: 1rem;">${errorGuidance}</div>
        <div style="display: flex; gap: 0.5rem; justify-content: center;">
          <button onclick="window.location.reload()" style="padding: 0.75rem 1.5rem; background: white; color: #dc2626; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600;">
            Restart Application
          </button>
          <button onclick="window.open('mailto:support@inboxai.example.com', '_blank')" style="padding: 0.75rem 1.5rem; background: transparent; color: white; border: 2px solid white; border-radius: 0.75rem; cursor: pointer; font-weight: 600;">
            Get Help
          </button>
        </div>
      </div>
    `;
  }
};

// Clean application initialization - REMOVED browser feature detection
const initializeApp = () => {
  // Check if user has existing auth token
  const existingToken = localStorage.getItem('auth_token');
  if (existingToken) {
    console.log('🔐 Found existing authentication token');
  }
  
  // Proceed with app initialization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderApp);
  } else {
    renderApp();
  }
};

// Enhanced Hot Module Replacement for development
if (import.meta.hot) {
  import.meta.hot.accept('./App.jsx', () => {
    console.log('🔁 Hot reloading InboxAI App component...');
    
    // Preserve auth state during hot reload
    const preservedAuthToken = localStorage.getItem('auth_token');
    
    renderApp();
    
    // Restore auth state if it was cleared during reload
    if (preservedAuthToken && !localStorage.getItem('auth_token')) {
      localStorage.setItem('auth_token', preservedAuthToken);
    }
  });
  
  // Handle hot reload errors
  import.meta.hot.dispose(() => {
    console.log('🧹 Cleaning up before hot reload...');
  });
}

// Initialize the enhanced application
initializeApp();

// Export for testing and external integration
export { renderApp, ErrorBoundary };
