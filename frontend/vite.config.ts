import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
// 启用Vue插件
  plugins: [vue()],
  resolve: { alias: { '@sky': fileURLToPath(new URL('../shared', import.meta.url)) } },
  //配置开发服务器，监听端口5173
  server: {
    port: 5173,
    strictPort: true,
    host: '127.0.0.1',
    fs: { allow: ['..'] },
  // 配置后端代理，将API请求转发到8000端口
    proxy: {
      '/agent-api': { target: 'http://127.0.0.1:8002', changeOrigin: true, rewrite: (path) => path.replace(/^\/agent-api/, '') },
      '/java-api': { target: 'http://127.0.0.1:8081', changeOrigin: true, rewrite: (path) => path.replace(/^\/java-api/, '') },
      // 将/api开头的请求转发到http://127.0.0.1:8000
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})
