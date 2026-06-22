import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Development server configuration
  server: {
    port: 3000,
    host: true, // Listen on all addresses
    proxy: {
      '/api': {
        // Proxy target: backend base URL (without /api/v1)
        // Default to localhost during local development so the dev server proxies to a local backend.
        // If VITE_API_URL is provided and does not point to localhost, use it instead (useful for Docker/dev containers).
        target: (process.env.VITE_API_URL && !process.env.VITE_API_URL.includes('localhost')) ? process.env.VITE_API_URL : 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // Pass through the path as-is (frontend uses /api/v1, backend expects /api/v1)
        rewrite: (path) => path
      },
      '/ws': {
        target: (process.env.VITE_WS_URL && !process.env.VITE_WS_URL.includes('localhost')) ? process.env.VITE_WS_URL : 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      }
    },

    // Enable hot module replacement
    hmr: {
      overlay: true
    }
  },
  
  // Build configuration - UPDATED for better compatibility
  build: {
    outDir: 'dist',
    sourcemap: false, // Disable sourcemaps for production
    target: 'es2017', // Updated to ES2017 for better compatibility
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['lucide-react'],
          utils: ['date-fns', 'clsx']
        }
      }
    },
    // Chunk size warning limit
    chunkSizeWarningLimit: 1200,
    // Minify options
    minify: 'esbuild'
  },
  
  // Resolve configuration
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@pages': resolve(__dirname, 'src/pages'),
      '@hooks': resolve(__dirname, 'src/hooks'),
      '@services': resolve(__dirname, 'src/services'),
      '@utils': resolve(__dirname, 'src/utils'),
      '@styles': resolve(__dirname, 'src/styles'),
      '@context': resolve(__dirname, 'src/context')
    }
  },
  
  // CSS configuration
  css: {
    devSourcemap: false
  },
  
  // Environment variables - FIXED for Vercel
  define: {
    // Default to localhost for host development; Docker can override via env
    'process.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || 'http://localhost:8000'),
    'process.env.VITE_WS_URL': JSON.stringify(process.env.VITE_WS_URL || 'ws://localhost:8000'),
    'process.env.VITE_APP_NAME': JSON.stringify(process.env.VITE_APP_NAME)
  },
  
  // Optimize dependencies
  optimizeDeps: {
    include: ['react', 'react-dom', 'lucide-react'],
    exclude: ['@vitejs/plugin-react']
  },
  
  // Preview configuration (for production build preview)
  preview: {
    port: 3000,
    host: true
  }
})
