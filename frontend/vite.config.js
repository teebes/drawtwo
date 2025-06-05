import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // Bind to all interfaces for Docker
    port: 3000,
    proxy: {
      '/api': {
        // Use backend service name in Docker, localhost for local dev
        target: process.env.NODE_ENV === 'development' && process.env.DOCKER
          ? 'http://backend:8000'
          : 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})