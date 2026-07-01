import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/health': 'http://localhost:8001',
      '/ingest': 'http://localhost:8001',
      '/query': 'http://localhost:8001',
      '/auth': 'http://localhost:8001',
      '/chats': 'http://localhost:8001',
    },
  },
})
