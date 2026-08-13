import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // En dev apunta al backend local; en build la API es mismo origen (/api/v1)
  const devApiTarget = env.VITE_API_URL
    ? env.VITE_API_URL.replace('/api/v1', '')
    : 'http://127.0.0.1:8010'

  return {
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 3010,
      proxy: {
        '/api': { target: devApiTarget, changeOrigin: true },
        '/media': { target: devApiTarget, changeOrigin: true },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          // Separar vendor para cacheo eficiente
          manualChunks: {
            vendor: ['react', 'react-dom'],
          },
        },
      },
    },
  }
})

