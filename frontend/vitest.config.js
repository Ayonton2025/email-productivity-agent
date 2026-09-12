import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/__tests__/setupTests.js',
    testTimeout: 15000,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/__tests__/**', 'src/**/*.{test,spec}.{js,jsx}'],
      reporter: ['text', 'json-summary', 'html'],
      // Ratchet the whole-source baseline while allowing the clean-checkout suite to run.
      thresholds: { lines: 30, statements: 30, functions: 26, branches: 20 },
    },
  },
})
