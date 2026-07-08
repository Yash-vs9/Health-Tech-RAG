import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/health': 'http://localhost:8000',
      '/ingest': 'http://localhost:8000',
      '/query': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/chats': 'http://localhost:8000',
    },
  },
})
