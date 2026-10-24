import type { Feature as GeoFeature, Geometry } from 'geojson'
export const categories = [
  { id: 'industrial', label: 'Industrial facilities', color: '#137c75', short: 'Industrial' },
  { id: 'industrial_park', label: 'Industrial land use / parks', color: '#299a80', short: 'Areas' },
  { id: 'warehouse', label: 'Warehouses', color: '#d6933b', short: 'Warehouses' },
  { id: 'logistics_hub', label: 'Logistics hubs', color: '#7265b3', short: 'Hubs' },
  { id: 'port', label: 'Ports', color: '#347cbb', short: 'Ports' },
  { id: 'airport', label: 'Airports', color: '#509baf', short: 'Airports' },
  { id: 'road', label: 'Major roads', color: '#b36d58', short: 'Roads' },
  { id: 'rail', label: 'Rail infrastructure', color: '#818e9b', short: 'Rail' },
  { id: 'study_area', label: 'Study polygons', color: '#609b91', short: 'Study areas' },
] as const
export type CategoryId = typeof categories[number]['id']
export interface Properties {
  name: string; categories: CategoryId[]; source: string; license?: string|null; source_id: string;
  dataset_id: string; imported_at: string; synthetic: boolean;
  boundary_status: string; attributes: Record<string, unknown>
}
export type SpatialFeature = GeoFeature<Geometry, Properties> & { id: string }
export interface SearchMeta {
  mode: 'fixture' | 'postgis'; crs: 'EPSG:4326'; total: number; returned: number;
  offset: number; limit: number; has_more: boolean; category_counts: Record<string, number>;
  missing_categories: string[]; failed_categories: string[]; warnings: string[]; attribution: string
}
export interface SearchResult { type: 'FeatureCollection'; features: SpatialFeature[]; meta: SearchMeta }
export interface Health { status: string; version: string; mode: 'fixture' | 'postgis'; database_configured: boolean; limitations: string[] }
export type Bbox = [number, number, number, number]
export type Tool = 'select' | 'point' | 'line' | 'polygon' | 'distance' | 'area'
export const studyAreas: {id: string; name: string; bbox: Bbox; description: string}[] = [
  {id: 'klang', name: 'Klang Valley', bbox: [101.25, 2.72, 101.87, 3.4], description: 'Approximate viewing extent · no verified boundary'},
  {id: 'north', name: 'Northern corridor', bbox: [100.1, 5.0, 100.9, 5.75], description: 'Approximate viewing extent · no verified boundary'},
  {id: 'south', name: 'Johor corridor', bbox: [103.2, 1.15, 104.3, 2.0], description: 'Approximate viewing extent · no verified boundary'},
  {id: 'automotive', name: 'Tanjong Malim corridor', bbox: [101.3, 3.5, 101.75, 3.95], description: 'Approximate viewing extent · no facility boundaries'},
  {id: 'malaysia', name: 'Malaysia', bbox: [99.5, 0.7, 119.7, 7.5], description: 'Nationwide viewing extent · no administrative boundary'},
]
export const categoryLabel = (id: string) => categories.find(c => c.id === id)?.label ?? id
