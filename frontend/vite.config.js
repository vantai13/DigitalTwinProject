import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig(({ mode }) => {
  // Load env file based on `mode` (development, production, etc.)
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [
      vue(),
      env.VITE_ENABLE_DEVTOOLS === 'true' ? vueDevTools() : null,
    ].filter(Boolean),
    
    server: {
      host: env.VITE_DEV_HOST || 'localhost',
      port: parseInt(env.VITE_DEV_PORT || 5173),
    },
    
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
    
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
    }
  }
})