import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // 确保构建出的 HTML 采用相对路径引入 JS/CSS
  server: {
    port: 8899,
    strictPort: true,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:23851',
        changeOrigin: true
      }
    }
  }
})
