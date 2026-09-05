import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // '@/' resolves to frontend/src - use it instead of deep relative paths.
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    // Same-origin proxy to FastAPI. Keeps the auth cookie working and means the
    // app never needs CORS. Do NOT add CORSMiddleware on the backend - a
    // cross-origin cookie would need SameSite=None; Secure, which does not work
    // over plain-HTTP localhost.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
})
