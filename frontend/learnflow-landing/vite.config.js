import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev: / and same-origin API proxy. Production: static bundle mounted under
// FastAPI /static/landing/, with GET / served by an opt-in backend route.
export default defineConfig(({command}) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/landing/' : '/',
  server: {
    host: true,
    proxy: {
      '/api': {target: process.env.LEARNFLOW_BACKEND_URL || 'http://127.0.0.1:8000', changeOrigin: true},
      '/healthz': {target: process.env.LEARNFLOW_BACKEND_URL || 'http://127.0.0.1:8000', changeOrigin: true},
    },
  },
}));
