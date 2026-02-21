import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => {
          // Only rewrite /api/auth/* to /auth/*
          // Keep /api/v1/* as is since backend has /api/v1 endpoints
          if (path.startsWith('/api/auth')) {
            return path.replace(/^\/api/, '');
          }
          return path;
        },
        configure: (proxy, _options) => {
          proxy.on('proxyRes', (proxyRes, _req, _res) => {
            proxyRes.headers['Access-Control-Allow-Origin'] = '*';
            proxyRes.headers['Access-Control-Allow-Credentials'] = 'true';
            proxyRes.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS';
            proxyRes.headers['Access-Control-Allow-Headers'] = '*';
          });
        },
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
