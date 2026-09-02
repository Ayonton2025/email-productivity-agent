export default function AuthLoadingScreen({ message = 'Loading...' }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600">
      <div className="loading-container">
        <div className="logo-loader">✉️</div>
        <div className="loading-spinner"></div>
        <div className="loading-text">Bylix Email</div>
        <div className="loading-subtext">{message}</div>
      </div>
    </div>
  )
}
