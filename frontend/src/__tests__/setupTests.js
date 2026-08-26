import '@testing-library/jest-dom/vitest'

// Mock window.Stripe and window.PaystackPop to avoid runtime errors in tests
window.Stripe = () => ({ redirectToCheckout: () => Promise.resolve() })
window.PaystackPop = { setup: () => ({ openIframe: () => {} }) }
