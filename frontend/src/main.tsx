import { setWorkerUrl } from 'maplibre-gl'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import 'maplibre-gl/dist/maplibre-gl.css'
import './styles/global.css'
import './styles/phase2.css'
import './styles/routing.css'
import './styles/analytics.css'
setWorkerUrl('/maplibre-worker.cjs')
const client = new QueryClient({ defaultOptions: { queries: { staleTime: 30000, retry: 1, refetchOnWindowFocus: false } } })
ReactDOM.createRoot(document.getElementById('root')!).render(<QueryClientProvider client={client}><App /></QueryClientProvider>)
