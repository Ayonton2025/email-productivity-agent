import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import { API_BASE_URL } from './services/api'
import { logger } from './utils/logger'

// Import global styles
import './styles/globals.css'

// Enhanced performance monitoring with AI operation tracking
const withPerformanceMonitoring = (WrappedComponent) => {
  return function PerformanceMonitoredApp(props) {
    const [performanceMetrics, setPerformanceMetrics] = React.useState({
      appLoadTime: null,
      aiOperationTimes: [],
      networkRequests: [],
      authOperations: [],
    })

    React.useEffect(() => {
      // Measure initial app load time
      const startTime = performance.now()

      // Track API performance including auth and email operations
      const originalFetch = window.fetch
      window.fetch = function (...args) {
        const start = performance.now()
        return originalFetch.apply(this, args).then((response) => {
          const duration = performance.now() - start
          const url = args[0]

          // Track different types of operations
          if (url?.includes('/api/auth/')) {
            setPerformanceMetrics((prev) => ({
              ...prev,
              authOperations: [
                ...prev.authOperations,
                {
                  endpoint: url,
                  duration: duration,
                  timestamp: new Date().toISOString(),
                },
              ].slice(-10),
            }))
          } else if (url?.includes('/api/email-accounts/')) {
            setPerformanceMetrics((prev) => ({
              ...prev,
              aiOperationTimes: [
                ...prev.aiOperationTimes,
                {
                  endpoint: url,
                  duration: duration,
                  type: 'email_provider',
                  timestamp: new Date().toISOString(),
                },
              ].slice(-20),
            }))
          } else if (url?.includes('/api/') || url?.includes('openai')) {
            setPerformanceMetrics((prev) => ({
              ...prev,
              aiOperationTimes: [
                ...prev.aiOperationTimes,
                {
                  endpoint: url,
                  duration: duration,
                  type: 'ai_service',
                  timestamp: new Date().toISOString(),
                },
              ].slice(-20),
            }))
          }

          return response
        })
      }

      return () => {
        const mountTime = performance.now() - startTime
        window.fetch = originalFetch // Restore original fetch

        setPerformanceMetrics((prev) => ({
          ...prev,
          appLoadTime: mountTime,
        }))

        if (import.meta.env.DEV) {
          logger.debug(`🚀 Bylix Email mounted in ${mountTime.toFixed(2)}ms`)

          // Performance insights
          const aiOps = performanceMetrics.aiOperationTimes.length
          const authOps = performanceMetrics.authOperations.length

          logger.debug(`📊 Performance Summary:`)
          logger.debug(`   - AI Operations: ${aiOps}`)
          logger.debug(`   - Auth Operations: ${authOps}`)

          if (mountTime > 1000) {
            logger.warn('⚠️  App mount time is high. Consider optimizing initial load.')
          }
        }

        // Log to analytics in production
        if (import.meta.env.PROD) {
          if (window.gtag) {
            window.gtag('event', 'app_load', {
              load_time: Math.round(mountTime),
              ai_operations: performanceMetrics.aiOperationTimes.length,
              auth_operations: performanceMetrics.authOperations.length,
            })
          }
        }
      }
    }, [])

    // Monitor service health including auth and email providers
    React.useEffect(() => {
      const checkServiceHealth = async () => {
        try {
          const apiBaseUrl = API_BASE_URL.startsWith('http')
            ? API_BASE_URL
            : `${window.location.origin}${API_BASE_URL.startsWith('/') ? '' : '/'}${API_BASE_URL}`

          // Check auth service
          const authResponse = await fetch(`${apiBaseUrl}/me`, {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
            },
          })

          if (!authResponse.ok && authResponse.status !== 401) {
            logger.warn('⚠️  Auth service health check failed')
          }

          // Check AI service health
          const aiResponse = await fetch(`${apiBaseUrl}/health/ai`)
          if (!aiResponse.ok) {
            logger.warn('⚠️  AI service health check failed')
          }
        } catch (error) {
          logger.warn('⚠️  Service health check failed:', error)
        }
      }

      // Check service health every 5 minutes
      const healthCheckInterval = setInterval(checkServiceHealth, 5 * 60 * 1000)

      return () => clearInterval(healthCheckInterval)
    }, [])

    return <WrappedComponent {...props} />
  }
}

// Enhanced App component with AI capabilities monitoring
const EnhancedApp = withPerformanceMonitoring(App)

// Enhanced Strict Mode wrapper with development tools
const StrictModeWrapper = ({ children }) => {
  const [showDevTools, setShowDevTools] = React.useState(false)

  React.useEffect(() => {
    if (import.meta.env.DEV) {
      const handleKeyPress = (event) => {
        // Ctrl+Shift+D to toggle dev tools
        if (event.ctrlKey && event.shiftKey && event.key === 'D') {
          setShowDevTools((prev) => !prev)
        }
      }

      window.addEventListener('keydown', handleKeyPress)
      return () => window.removeEventListener('keydown', handleKeyPress)
    }
    return undefined
  }, [])

  // Development-only features
  if (import.meta.env.DEV) {
    return (
      <React.StrictMode>
        {children}
        {showDevTools && <DevelopmentTools />}
      </React.StrictMode>
    )
  }

  return <React.StrictMode>{children}</React.StrictMode>
}

// Enhanced Development tools component with auth and email provider info
const DevelopmentTools = () => {
  const [metrics, setMetrics] = React.useState({})
  const [authStatus, setAuthStatus] = React.useState('Checking...')

  React.useEffect(() => {
    // Check auth status
    const token = localStorage.getItem('auth_token')
    if (token) {
      setAuthStatus('Authenticated')
    } else {
      setAuthStatus('Not Authenticated')
    }

    // Simulate metrics collection
    const interval = setInterval(() => {
      setMetrics({
        memory: (performance.memory?.usedJSHeapSize / 1048576).toFixed(2) + ' MB',
        connections: 'Active',
        aiStatus: 'Connected',
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="fixed bottom-4 right-4 bg-gray-800 text-white p-4 rounded-lg shadow-lg text-xs z-50 max-w-xs">
      <div className="font-bold mb-2">🧠 Bylix Email Dev Tools</div>
      <div className="space-y-1">
        <div>Memory: {metrics.memory}</div>
        <div>
          Auth:{' '}
          <span className={authStatus === 'Authenticated' ? 'text-green-400' : 'text-yellow-400'}>{authStatus}</span>
        </div>
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
            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
            // Open /docs endpoint
            window.open(`${apiUrl}/docs`, '_blank')
          }}
          className="flex-1 bg-indigo-600 hover:bg-indigo-700 px-2 py-1 rounded text-xs"
        >
          API Docs
        </button>
        <button
          onClick={() => {
            localStorage.removeItem('auth_token')
            window.location.reload()
          }}
          className="flex-1 bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs"
        >
          Clear Auth
        </button>
      </div>
    </div>
  )
}

// Clean main render function without browser detection
const renderApp = () => {
  const rootElement = document.getElementById('root')

  if (!rootElement) {
    logger.error('Root element not found!')

    // Create fallback UI
    document.body.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; font-family: system-ui;">
        <div style="text-align: center;">
          <div style="font-size: 2rem; margin-bottom: 1rem;">❌</div>
          <h1 style="font-size: 1.5rem; margin-bottom: 0.5rem;">Bylix Email Failed to Load</h1>
          <p style="margin-bottom: 1rem;">Critical error: Root element missing</p>
          <button onclick="window.location.reload()" style="padding: 0.5rem 1rem; background: white; color: #6366f1; border: none; border-radius: 0.5rem; cursor: pointer;">
            Restart Application
          </button>
        </div>
      </div>
    `
    return
  }

  try {
    const root = ReactDOM.createRoot(rootElement)

    root.render(
      <StrictModeWrapper>
        <ErrorBoundary>
          <EnhancedApp />
        </ErrorBoundary>
      </StrictModeWrapper>
    )

    // Enhanced initialization logging with new features
    logger.debug(`
    🚀 Bylix Email Initialized Successfully!
    
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
    `)

    // Enhanced loading indicator removal with smooth transition
    const loadingContainer = document.querySelector('.loading-container')
    if (loadingContainer) {
      // Add success message before removing
      const successMessage = document.createElement('div')
      successMessage.className = 'loading-success'
      successMessage.innerHTML = `
        <div style="text-align: center; color: white; margin-top: 1rem;">
          <div style="font-size: 2rem;">🎉</div>
          <div>Bylix Email Ready!</div>
          <div style="font-size: 0.8rem; margin-top: 0.5rem; opacity: 0.8;">
            Now with User Authentication & Real Email Support
          </div>
        </div>
      `
      loadingContainer.appendChild(successMessage)

      setTimeout(() => {
        loadingContainer.style.opacity = '0'
        loadingContainer.style.transform = 'scale(0.95)'
        loadingContainer.style.transition = 'all 0.5s ease'

        setTimeout(() => {
          if (loadingContainer.parentNode) {
            loadingContainer.parentNode.removeChild(loadingContainer)
          }
        }, 500)
      }, 1000)
    }
  } catch (error) {
    logger.error('💥 Failed to initialize Bylix Email:', error)

    // Enhanced error UI with specific guidance
    let errorGuidance = 'Please refresh the page and try again.'

    if (error.message?.includes('ReactDOM')) {
      errorGuidance = 'This might be a browser compatibility issue. Try updating your browser.'
    } else if (error.message?.includes('memory')) {
      errorGuidance = 'Your device is low on memory. Try closing other tabs and refresh.'
    } else if (error.message?.includes('auth')) {
      errorGuidance = 'Authentication system initialization failed. Please clear browser data and try again.'
    }

    rootElement.innerHTML = `
      <div class="loading-container" style="background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);">
        <div style="font-size: 3rem; margin-bottom: 1rem;">💥</div>
        <div class="loading-text" style="font-size: 1.5rem;">Bylix Email Failed to Start</div>
        <div class="loading-subtext" style="margin-bottom: 1rem;">${errorGuidance}</div>
        <div style="display: flex; gap: 0.5rem; justify-content: center;">
          <button onclick="window.location.reload()" style="padding: 0.75rem 1.5rem; background: white; color: #dc2626; border: none; border-radius: 0.75rem; cursor: pointer; font-weight: 600;">
            Restart Application
          </button>
          <button onclick="window.open('mailto:support@bylix.email', '_blank')" style="padding: 0.75rem 1.5rem; background: transparent; color: white; border: 2px solid white; border-radius: 0.75rem; cursor: pointer; font-weight: 600;">
            Get Help
          </button>
        </div>
      </div>
    `
  }
}

// Clean application initialization - REMOVED browser feature detection
const initializeApp = () => {
  // Check if user has existing auth token
  const existingToken = localStorage.getItem('auth_token')
  if (existingToken) {
    logger.debug('🔐 Found existing authentication token')
  }

  // Proceed with app initialization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderApp)
  } else {
    renderApp()
  }
}

// Enhanced Hot Module Replacement for development
if (import.meta.hot) {
  import.meta.hot.accept('./App.jsx', () => {
    logger.debug('🔁 Hot reloading Bylix Email App component...')

    // Preserve auth state during hot reload
    const preservedAuthToken = localStorage.getItem('auth_token')

    renderApp()

    // Restore auth state if it was cleared during reload
    if (preservedAuthToken && !localStorage.getItem('auth_token')) {
      localStorage.setItem('auth_token', preservedAuthToken)
    }
  })

  // Handle hot reload errors
  import.meta.hot.dispose(() => {
    logger.debug('🧹 Cleaning up before hot reload...')
  })
}

// Initialize the enhanced application
initializeApp()

// Export for testing and external integration
export { renderApp, ErrorBoundary }
