import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { Agent } from 'node:http'
// Avoid reusing sockets that Uvicorn has already closed after its idle timeout.
const apiProxy=()=>({target:'http://127.0.0.1:8000',changeOrigin:true,agent:new Agent({keepAlive:false}),proxyTimeout:25000,timeout:30000})
export default defineConfig({
  plugins: [react(), tailwindcss(), {
    name: 'classic-map-worker-mime',
    configureServer(server) { server.middlewares.use((req, res, next) => { if(req.url?.startsWith('/maplibre-worker.cjs')) res.setHeader('Content-Type', 'application/javascript'); next() }) },
    configurePreviewServer(server) { server.middlewares.use((req, res, next) => { if(req.url?.startsWith('/maplibre-worker.cjs')) res.setHeader('Content-Type', 'application/javascript'); next() }) },
  }],
  server: { port: 5173, strictPort: true, proxy: { '/api/spatial': {...apiProxy(),proxyTimeout:55000,timeout:60000}, '/api/analysis': {...apiProxy(),proxyTimeout:55000,timeout:60000}, '/api/routing': {...apiProxy(),proxyTimeout:55000,timeout:60000}, '/api/geoai': {...apiProxy(),proxyTimeout:175000,timeout:180000}, '/api': apiProxy(), '/health': apiProxy(), '/ready': apiProxy() } },
  build: { rollupOptions: { output: { manualChunks(id) {
    if (id.includes('maplibre-gl')) return 'maplibre'
    if (id.includes('recharts') || id.includes('d3-')) return 'charts'
  } } } },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.ts', css: false },
})
