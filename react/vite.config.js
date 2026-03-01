import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Keep production assets rooted at /assets/... so deep-link refreshes don't resolve to nested paths.
  base: '/',
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
});
