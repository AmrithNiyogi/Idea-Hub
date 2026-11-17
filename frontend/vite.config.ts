import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

/**
 * Vite app config + Vitest quality gates.
 *
 * Coverage gate (≥85% lines/functions/branches/statements) applies to the
 * testable core — `api`, `auth`, `utils`, `constants`, and presentational
 * `components` — not full page shells (large React Router + data-fetch UIs).
 * See README “Quality gates”.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    // Hostnames only (no https://). Add each ngrok hostname you tunnel through.
    allowedHosts: [
      '*',
      'ddca-106-51-110-255.ngrok-free.app',
      '9844-106-51-110-255.ngrok-free.app',
      '5990-106-51-110-255.ngrok-free.app'
    ],
    proxy: {
      // Same-origin /api + /uploads → uvicorn. Required for HTTPS ngrok UI
      // (browsers block mixed-content XHR to http://localhost:8000).
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    /** Fail-fast: stop the run on the first failing test file / assertion. */
    bail: 1,
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'text-summary', 'html', 'lcov'],
      reportsDirectory: './coverage',
      include: [
        'src/api/**/*.{ts,tsx}',
        'src/auth/**/*.{ts,tsx}',
        'src/utils/**/*.{ts,tsx}',
        'src/constants/**/*.{ts,tsx}',
        'src/components/**/*.{ts,tsx}',
      ],
      exclude: [
        'src/**/*.d.ts',
        'src/test/**',
        /** Large SVG path map — smoke-tested via Icon renders in component specs. */
        'src/components/Icons.tsx',
        /** Shell / panels need full app routing; covered indirectly via Login + IdeaCard. */
        'src/components/shell/**',
        'src/components/CollabTrackerPanel.tsx',
      ],
      thresholds: {
        lines: 85,
        functions: 85,
        branches: 85,
        statements: 85,
      },
    },
  },
});
