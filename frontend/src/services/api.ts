import type { Bbox, CategoryId, Health, SearchResult } from '../types'
export const apiBase = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
export async function request<T>(path: string, signal?: AbortSignal, options: RequestInit = {}, timeoutMs=30000): Promise<T> {
  const timeout = AbortSignal.timeout(timeoutMs)
  const response = await fetch(apiBase + path, { ...options, signal: signal ? AbortSignal.any([signal, timeout]) : timeout })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.error?.message ?? `API request failed (${response.status}). Check that FastAPI is running.`)
  }
  return response.json() as Promise<T>
}
export const getHealth = (signal?: AbortSignal) => request<Health>('/health', signal)
export interface SearchFilters { q: string; categories: CategoryId[]; bbox?: Bbox; center?: [number, number]; radius?: number; offset: number }
export function searchFeatures(filters: SearchFilters, signal?: AbortSignal, limit=250) {
  const params = new URLSearchParams({ q: filters.q, limit: String(limit), offset: String(filters.offset) })
  filters.categories.forEach(c => params.append('categories', c))
  if (filters.bbox) params.set('bbox', filters.bbox.join(','))
  if (filters.center && filters.radius) {
    params.set('center', filters.center.join(',')); params.set('radius_km', String(filters.radius))
  }
  return request<SearchResult>('/api/industrial/features?' + params.toString(), signal)
}
export function downloadGeoJSON(data: object, name = 'logistimap-query.geojson') {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/geo+json' }))
  const link = document.createElement('a'); link.href = url; link.download = name; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export function parseCoordinates(text: string): [number, number] | null {
  const parts = text.trim().split(/[,\s]+/)
  if (parts.length !== 2 || parts.some(p => p === '')) return null
  const values = parts.map(Number)
  if (!values.every(Number.isFinite) || Math.abs(values[0]) > 180 || Math.abs(values[1]) > 90) return null
  return [values[0], values[1]]
}

// Map/export loads every result up to an explicit 10,000-object client safety cap.
// The attribute table retains independent 250-record pagination.
export async function searchMapFeatures(filters:SearchFilters,signal?:AbortSignal):Promise<SearchResult>{
  const first=await searchFeatures({...filters,offset:0},signal,1000)
  const features=[...first.features]
  for(let offset=1000;offset<Math.min(first.meta.total,10000);offset+=1000){
    const page=await searchFeatures({...filters,offset},signal,1000)
    features.push(...page.features)
  }
  const unique=[...new Map(features.map(f=>[f.id,f])).values()]
  return {...first,features:unique,meta:{...first.meta,offset:0,limit:10000,returned:unique.length,
    has_more:first.meta.total>unique.length,
    warnings:[...first.meta.warnings.filter(w=>!w.includes('paginated')),
      ...(first.meta.total>10000?['Map/export capped at 10,000 features. Narrow the query; the attribute table can page through the remaining records.']:[])]}}
}
