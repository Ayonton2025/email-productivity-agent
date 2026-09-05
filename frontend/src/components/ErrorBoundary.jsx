import React from 'react'
import { logger } from '../utils/logger'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorType: 'general',
    }
  }

  static getDerivedStateFromError(error) {
    let errorType = 'general'

    if (error.message?.includes('NetworkError') || error.message?.includes('Failed to fetch')) {
      errorType = 'network'
    } else if (error.message?.includes('OpenAI') || error.message?.includes('API')) {
      errorType = 'ai_service'
    } else if (error.message?.includes('OAuth') || error.message?.includes('authentication')) {
      errorType = 'auth'
    } else if (
      error.message?.includes('Email provider') ||
      error.message?.includes('Gmail') ||
      error.message?.includes('Outlook')
    ) {
      errorType = 'email_provider'
    }

    return { hasError: true, errorType }
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ error, errorInfo })
    logger.error('Bylix Email Error Boundary caught an error:', {
      error: error.toString(),
      errorType: this.state.errorType,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
    })

    if (import.meta.env.PROD) {
      this.reportErrorToService(error)
    }
  }

  reportErrorToService(error) {
    try {
      if (window.gtag) {
        window.gtag('event', 'exception', {
          description: error.toString(),
          fatal: true,
          error_type: this.state.errorType,
        })
      }
    } catch (reportingError) {
      logger.warn('Error reporting failed:', reportingError)
    }
  }

  getErrorMessage() {
    const messages = {
      network: {
        title: 'Connection Issue',
        description: "We're having trouble connecting to our services. Please check your internet connection.",
        action: 'Check Connection',
      },
      ai_service: {
        title: 'AI Service Temporarily Unavailable',
        description: 'Our AI features are currently experiencing issues. Basic email functions remain available.',
        action: 'Retry AI Features',
      },
      auth: {
        title: 'Authentication Error',
        description: 'There was an issue with your session. Please sign in again.',
        action: 'Sign In Again',
      },
      email_provider: {
        title: 'Email Provider Connection Issue',
        description: 'There was an issue with your email provider connection. Please reconnect your account.',
        action: 'Reconnect Account',
      },
      general: {
        title: 'Something went wrong',
        description: "We're sorry, but the application encountered an unexpected error.",
        action: 'Reload Application',
      },
    }

    return messages[this.state.errorType] || messages.general
  }

  handleRecoveryAction = () => {
    const { errorType } = this.state

    switch (errorType) {
      case 'auth':
        localStorage.removeItem('auth_token')
        window.location.href = '/login'
        break
      case 'email_provider':
        window.location.hash = '#email-accounts'
        this.setState({ hasError: false, error: null, errorInfo: null })
        break
      default:
        window.location.reload()
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const errorMessage = this.getErrorMessage()

    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-red-100 flex items-center justify-center p-4 dark:from-red-900 dark:to-red-800">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-6 text-center dark:bg-gray-800">
          <h2 className="text-xl font-semibold text-gray-900 mb-2 dark:text-white">{errorMessage.title}</h2>
          <p className="text-gray-600 mb-4 dark:text-gray-300">{errorMessage.description}</p>
          {import.meta.env.DEV && this.state.error && (
            <details className="text-left bg-gray-50 rounded p-3 mb-4 text-sm dark:bg-gray-700">
              <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-300">
                Error Details (Development)
              </summary>
              <p className="text-red-600 dark:text-red-400 font-mono text-xs">{this.state.error.toString()}</p>
              <pre className="text-gray-600 dark:text-gray-400 text-xs mt-2 overflow-auto max-h-32">
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
          <div className="flex gap-3 justify-center">
            <button
              onClick={this.handleRecoveryAction}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              {errorMessage.action}
            </button>
            {(this.state.errorType === 'email_provider' || this.state.errorType === 'auth') && (
              <button
                onClick={() => {
                  window.location.href = this.state.errorType === 'email_provider' ? '#email-accounts' : '/login'
                  this.setState({ hasError: false, error: null, errorInfo: null })
                }}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                {this.state.errorType === 'email_provider' ? 'Go to Email Accounts' : 'Go to Sign In'}
              </button>
            )}
            <button
              onClick={() => this.setState({ hasError: false, error: null, errorInfo: null })}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
              Try Again
            </button>
          </div>
          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-600">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Need help? Here are some options:</p>
            <div className="flex justify-center gap-4 text-xs">
              <button onClick={() => window.open('https://github.com/your-username/bylix-email/issues', '_blank')}>
                Report Issue
              </button>
              <button onClick={() => window.open('mailto:support@bylix.email', '_blank')}>Contact Support</button>
              <button onClick={() => window.open('https://bylix.email/docs', '_blank')}>Documentation</button>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

export default ErrorBoundary
