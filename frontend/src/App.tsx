import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDownToLine, ArrowRight, Bell, Boxes, Check, ChevronDown, CircleHelp, Database, Filter, Globe2, Layers, MapPin, Menu, Moon, RefreshCw, Search, Settings2, ShieldCheck, Sun, TriangleAlert, X } from 'lucide-react'
import {GeoAICopilot} from './features/GeoAICopilot'
import {SiteSelection} from './features/SiteSelection'
import { LogisticsOptimization } from './features/LogisticsOptimization'
import { AdvancedWorkspace } from './features/AdvancedWorkspace'
import { FreightRoutePlanner } from './features/FreightRoutePlanner'
import { Sidebar, moduleInfo } from './components/Sidebar'
import { Inspector } from './components/Inspector'
import { DiscoveryPanel } from './components/DiscoveryPanel'
import type { DiscoveryScope } from './services/discovery'
import { AttributeTable } from './components/AttributeTable'
import { Button } from './components/ui/button'
import { MapWorkspace, type MapHandle } from './features/MapWorkspace'
import { apiBase, downloadGeoJSON, getHealth, parseCoordinates, request, searchFeatures, searchMapFeatures, type SearchFilters } from './services/api'
import { useWorkspace } from './store/workspace'
import { categories, studyAreas, type Bbox, type CategoryId, type SpatialFeature } from './types'

const initialArea=studyAreas[0]
export default function App(){
  const initialModule=location.hash.replace('#','')
  const [active,setActive]=useState(moduleInfo[initialModule]?initialModule:'explorer')
  const [sidebarOpen,setSidebarOpen]=useState(false)
  const [areaId,setAreaId]=useState(initialArea.id)
  const [scopeLabel,setScopeLabel]=useState('Study extent')
  const [filters,setFilters]=useState<SearchFilters>({q:'',categories:[],bbox:initialArea.bbox,offset:0})
  const [searchText,setSearchText]=useState('')
  const [filtersOpen,setFiltersOpen]=useState(false)
  const [filterCategories,setFilterCategories]=useState<CategoryId[]>(categories.map(c=>c.id))
  const [radiusCenter,setRadiusCenter]=useState(''),[radiusKm,setRadiusKm]=useState('15')
  const [customBbox,setCustomBbox]=useState('')
  const [formError,setFormError]=useState('')
  const [inspectorTab,setInspectorTab]=useState('Layers')
  const [tableOpen,setTableOpen]=useState(true),[tableTab,setTableTab]=useState('attributes')
  const [logs,setLogs]=useState<string[]>([])
  const [theme,setTheme]=useState(()=>localStorage.getItem('logistimap-theme')??'light')
  const [statusOpen,setStatusOpen]=useState(false),[readiness,setReadiness]=useState('Not checked')
  const [checking,setChecking]=useState(false)
  const map=useRef<MapHandle>(null)
  const selected=useWorkspace(s=>s.selected),setSelected=useWorkspace(s=>s.setSelected)
  const visible=useWorkspace(s=>s.visible)
  const area=studyAreas.find(a=>a.id===areaId)??initialArea
  const addLog=useCallback((message:string)=>setLogs(logs=>[new Date().toLocaleTimeString('en-GB')+' · '+message,...logs].slice(0,100)),[])
  const health=useQuery({queryKey:['health'],queryFn:({signal})=>getHealth(signal),refetchInterval:60000})
  const features=useQuery({queryKey:['features',filters],queryFn:({signal})=>searchFeatures(filters,signal),enabled:!['geoai','sites','optimization','supply','routing','toolbox','clusters','accessibility','industrial-accessibility','saved-analyses','route-history','reports'].includes(active)})
  const allFeatures=useQuery({queryKey:['map-features',filters.q,filters.categories,filters.bbox,filters.center,filters.radius],queryFn:({signal})=>searchMapFeatures(filters,signal),enabled:!['geoai','sites','optimization','supply','routing','toolbox','clusters','accessibility','industrial-accessibility','saved-analyses','route-history','reports'].includes(active)})
  const mapData=allFeatures.data
  const data=features.data
  const applyDiscoveryScope=useCallback((scope:DiscoveryScope)=>{
    setFilters({q:'',categories:scope.categories??[],bbox:scope.bbox,center:scope.center,radius:scope.radius_km,offset:0})
    setSearchText('');setScopeLabel(scope.label)
    if(scope.bbox)map.current?.fit(scope.bbox)
    else if(scope.center){
      const [x,y]=scope.center,dy=(scope.radius_km??5)/110.574,dx=(scope.radius_km??5)/(111.32*Math.cos(y*Math.PI/180))
      map.current?.fit([x-dx,y-dy,x+dx,y+dy])
    }
  },[])

  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('logistimap-theme',theme)},[theme])
  useEffect(()=>{if(selected)setInspectorTab('Feature')},[selected])
  useEffect(()=>{setSelected(null)},[filters,setSelected])
  useEffect(()=>{setFilterCategories(filters.categories.length?filters.categories:categories.map(c=>c.id))},[filters.categories])
  useEffect(()=>{if(data)addLog('Query returned '+data.meta.returned+' of '+data.meta.total+' records · '+data.meta.mode+' mode · EPSG:4326')},[features.dataUpdatedAt,addLog])
  useEffect(()=>{if(features.error)addLog('Query failed: '+features.error.message)},[features.error,addLog])
  useEffect(()=>{const fn=()=>{const id=location.hash.replace('#','');if(moduleInfo[id])setActive(id)};window.addEventListener('hashchange',fn);return()=>window.removeEventListener('hashchange',fn)},[])
  function navigate(id:string){setActive(id);location.hash=id;setSidebarOpen(false);if(id==='warehouses')setFilters(f=>({...f,q:'',categories:['warehouse','logistics_hub'],offset:0}))}
  function selectArea(id:string){
    const next=studyAreas.find(a=>a.id===id)!
    setAreaId(id);setScopeLabel('Study extent');setRadiusCenter('');setCustomBbox('')
    setFilters(f=>({...f,bbox:next.bbox,center:undefined,radius:undefined,offset:0}));map.current?.fit(next.bbox)
    addLog('Study extent: '+next.name+' · approximate viewing extent, not a verified boundary.')
  }
  function submitSearch(event:FormEvent){
    event.preventDefault();setFormError('')
    const coordinates=parseCoordinates(searchText)
    if(coordinates){map.current?.flyTo(coordinates);addLog('Flew to longitude/latitude '+coordinates.join(', '));return}
    const named=studyAreas.find(a=>a.name.toLowerCase()===searchText.trim().toLowerCase())
    if(named){selectArea(named.id);setFilters(f=>({...f,q:'',offset:0}));return}
    setFilters(f=>({...f,q:searchText.trim(),offset:0}))
  }
  function applyFilters(event:FormEvent){
    event.preventDefault();setFormError('')
    let bbox:Bbox|undefined=area.bbox,center:[number,number]|undefined,radius:number|undefined
    if(customBbox.trim()){
      const parts=customBbox.split(',').map(v=>Number(v.trim()))
      if(parts.length!==4||parts.some(v=>!Number.isFinite(v))||parts[0]>=parts[2]||parts[1]>=parts[3]||parts[0]<-180||parts[2]>180||parts[1]<-90||parts[3]>90){setFormError('Use west,south,east,north in EPSG:4326, with west < east and south < north.');return}
      bbox=parts as Bbox
    }
    if(radiusCenter.trim()){
      center=parseCoordinates(radiusCenter)??undefined;radius=Number(radiusKm)
      if(!center||!Number.isFinite(radius)||radius<=0||radius>200){setFormError('Radius search needs valid longitude,latitude and a radius above 0 and at most 200 km.');return}
      bbox=undefined
    }
    setFilters(f=>({...f,categories:filterCategories.length===categories.length?[]:filterCategories,bbox,center,radius,offset:0}))
    setScopeLabel(center?'Radius':customBbox.trim()?'Custom extent':'Study extent');setFiltersOpen(false)
    if(bbox)map.current?.fit(bbox);else if(center)map.current?.flyTo(center)
  }
  function useMapExtent(){
    const bbox=map.current?.getBounds()
    if(!bbox){setFormError('Map bounds are unavailable until WebGL initializes.');return}
    setFilters(f=>({...f,bbox,center:undefined,radius:undefined,offset:0}));setScopeLabel('Map extent');setFormError('')
    addLog('Applied map viewport as EPSG:4326 bounding-box filter.')
  }
  function clearFilters(){
    setSearchText('');setRadiusCenter('');setCustomBbox('');setFilterCategories(categories.map(c=>c.id));setScopeLabel('Study extent');setFormError('')
    setFilters({q:'',categories:[],bbox:area.bbox,offset:0})
  }
  function chooseFeature(feature:SpatialFeature){
    setSelected(feature)
    if(feature.geometry.type==='Point')map.current?.flyTo(feature.geometry.coordinates as [number,number])
    else {
      const collect=(value:unknown):number[][]=>Array.isArray(value)&&typeof value[0]==='number'?[value as number[]]:Array.isArray(value)?value.flatMap(collect):[]
      if('coordinates' in feature.geometry){const coords=collect(feature.geometry.coordinates),xs=coords.map(p=>p[0]),ys=coords.map(p=>p[1]);map.current?.fit([Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)])}
    }
  }
  async function checkReadiness(){
    setChecking(true)
    try{const result=await request<Record<string,unknown>>('/ready');setReadiness(JSON.stringify(result,null,2))}
    catch(err){setReadiness(err instanceof Error?err.message:'Readiness check failed')}
    finally{setChecking(false)}
  }
  const module=moduleInfo[active]??moduleInfo.explorer
  const unavailable='phase' in module&&module.phase!==undefined
  const mode=data?.meta.mode??health.data?.mode
  const visibleCount=mapData?.features.filter(f=>f.properties.categories.some(c=>visible.includes(c))).length
  const geometryCount=new Set(mapData?.features.map(f=>f.geometry.type)).size
  const matchedCategories=Object.values(data?.meta.category_counts??{}).filter(n=>n>0).length
  return <div className="app-shell">
    <Sidebar active={active} onNavigate={navigate} open={sidebarOpen}/>
    {sidebarOpen&&<button className="sidebar-backdrop" aria-label="Close navigation" onClick={()=>setSidebarOpen(false)}/>}
    <div className="main-shell">
      <header className="topbar">
        <Button variant="ghost" size="icon" className="mobile-menu" aria-label="Open navigation" onClick={()=>setSidebarOpen(!sidebarOpen)}><Menu size={20}/></Button>
        <div className="breadcrumb">Workspace<span>/</span><strong>{module.label}</strong></div>
        <div className="topbar-actions">
          <button className="api-status" onClick={()=>setStatusOpen(!statusOpen)} aria-expanded={statusOpen}><span className={'status-dot '+(!health.data?'offline':'')}/>{health.data?'API connected':'API unavailable'}<ChevronDown size={12}/></button>
          <span className="topbar-divider"/>
          <Button variant="ghost" size="icon" aria-label={theme==='light'?'Switch to dark theme':'Switch to light theme'} onClick={()=>setTheme(theme==='light'?'dark':'light')}>{theme==='light'?<Moon size={17}/>:<Sun size={17}/>}</Button>
          <Button variant="ghost" size="icon" aria-label="Open operational status" onClick={()=>setStatusOpen(!statusOpen)}><Bell size={17}/></Button>
          <div className="user-placeholder" title="Local user placeholder; authentication unavailable">LM</div>
        </div>
      </header>
      {statusOpen&&<div className="operational-status"><div><strong>Operational status</strong><Button variant="ghost" size="icon" aria-label="Close operational status" onClick={()=>setStatusOpen(false)}><X size={15}/></Button></div><p>Backend: {health.error?health.error.message:health.data?'Connected · v'+health.data.version:'Checking…'}</p><p>Source mode: {mode??'Unknown'} · Database: {health.data?.database_configured?'configured, connection unverified':'not configured'}</p><Button variant="outline" size="sm" onClick={()=>{navigate('settings');setStatusOpen(false)}}>Connection diagnostics<ArrowRight size={13}/></Button></div>}
      <main>
        <div className="page-heading"><div><div className="eyebrow"><span className="tiny-line"/> INDUSTRIAL & LOGISTICS INTELLIGENCE</div><h1>{active==='explorer'?'Industrial GIS Explorer':module.label}</h1><p>Explore spatial data. Understand connections. Make informed decisions.</p></div><div className="heading-actions"><span className="foundation-badge">PHASE 7 · GEOAI INTELLIGENCE</span>{!['geoai','sites','optimization','supply','routing','toolbox','clusters','accessibility','industrial-accessibility','saved-analyses','route-history','reports'].includes(active)&&<Button variant="outline" disabled={!mapData?.features.length||allFeatures.isFetching} onClick={()=>mapData&&downloadGeoJSON(mapData)}><ArrowDownToLine size={14}/>Export GeoJSON</Button>}</div></div>
        {active==='geoai'?<GeoAICopilot onLog={addLog}/>:active==='sites'?<SiteSelection onLog={addLog}/>:['optimization','supply'].includes(active)?<LogisticsOptimization onLog={addLog}/>:['toolbox','clusters','accessibility','industrial-accessibility','saved-analyses','route-history','reports'].includes(active)?<AdvancedWorkspace module={active==='reports'?'saved-analyses':active} onLog={addLog}/>:active==='routing'?<FreightRoutePlanner mode={mode} onLog={addLog}/>:<>
        <div className={'data-banner '+(mode==='fixture'?'fixture-banner':'')} role="status"><div><TriangleAlert size={15}/><strong>{mode==='fixture'?'Synthetic fixture mode':mode==='postgis'?'Imported PostGIS dataset':'Awaiting data connection'}</strong><span>{mode==='fixture'?'Test features only. These are not real facilities, routes, or industrial boundaries.':mode==='postgis'?'Coverage depends on imported data and source quality.':'Start FastAPI to query data. No fallback records are displayed.'}</span></div><span className="banner-tag">{mode==='fixture'?'DEVELOPMENT DATA':'REAL SOURCE DATA'}</span></div>
        {unavailable&&<section className="module-message"><div className="module-message-icon"><module.icon size={24}/></div><div><span className="eyebrow">UNAVAILABLE · PHASE {module.phase}</span><h2>{module.label}</h2><p>This workflow is planned for a later phase. The GIS foundation below remains available; no analysis results have been generated for this module.</p></div><Button variant="outline" onClick={()=>navigate('explorer')}>Open GIS Explorer<ArrowRight size={14}/></Button></section>}
        {(active==='settings'||active==='data')&&<section className="configuration-panel"><div><span className="eyebrow">{active==='settings'?'ENVIRONMENT & CONNECTIONS':'DATA CATALOG'}</span><h2>{active==='settings'?'Workspace configuration':'Source and provenance'}</h2><p>{active==='settings'?'Mode, CORS and database credentials are configured only in backend environment variables.':'OSM discovery imports into PostGIS with source IDs, category memberships and retained job reports. File uploads remain unavailable.'}</p><dl><div><dt>API endpoint</dt><dd>{apiBase||'Vite proxy → 127.0.0.1:8000'}</dd></div><div><dt>Data mode</dt><dd>{mode??'Unknown'}</dd></div><div><dt>Coordinate reference</dt><dd>EPSG:4326 · longitude, latitude</dd></div><div><dt>Source attribution</dt><dd>{data?.meta.attribution??'No source loaded'}</dd></div></dl></div><div className="diagnostics"><ShieldCheck size={23}/><h3>Connection diagnostics</h3><p>Fixture readiness does not verify PostGIS. Database mode never falls back to fixtures.</p><Button variant="outline" disabled={checking} onClick={checkReadiness}><RefreshCw size={13}/>{checking?'Checking…':'Check readiness'}</Button><pre>{readiness}</pre><a href={(apiBase||'http://127.0.0.1:8000')+'/docs'} target="_blank" rel="noreferrer">Open API documentation ↗</a></div></section>}
        {active==='toolbox'&&<section className="toolbox-intro"><RulerIcon/><p><strong>Drawing & geodesic measurement available.</strong> Choose point, line, polygon, distance or area tools on the map, click vertices, then Finish. Backend validates geometry and calculates WGS84 geodesic units. Buffer, overlay and other advanced geoprocessing tools are unavailable until Phase 4.</p></section>}
        <DiscoveryPanel key={active==='data'?'catalog':'workspace'} mode={mode} onScope={applyDiscoveryScope} getBounds={()=>map.current?.getBounds()} onLog={addLog} defaultOpen={active==='data'}/>
        <div className="kpi-grid" aria-label="Current dataset summary">
          <div className="kpi"><span className="kpi-icon teal"><Boxes size={19}/></span><div><span>Matched records</span><strong>{data?.meta.total??'—'}</strong><small>{mode==='fixture'?'Synthetic test records':'Current query'}</small></div><span className="kpi-note">QUERY</span></div>
          <div className="kpi"><span className="kpi-icon ochre"><Layers size={19}/></span><div><span>Categories found</span><strong>{data?matchedCategories:'—'}<em>/ {filters.categories.length||categories.length}</em></strong><small>Overlapping memberships</small></div></div>
          <div className="kpi"><span className="kpi-icon blue"><Globe2 size={19}/></span><div><span>Geometry types</span><strong>{mapData?geometryCount:'—'}</strong><small>Across loaded map results</small></div></div>
          <div className="kpi"><span className="kpi-icon violet"><Database size={19}/></span><div><span>Data source</span><strong className="source-kpi">{mode==='fixture'?'Test fixture':mode==='postgis'?'PostGIS':'Not connected'}</strong><small>{mode==='fixture'?'Clearly labeled · not verified':'Provenance per feature'}</small></div></div>
        </div>
        <section className="gis-frame">
          <div className="query-toolbar"><form className="global-search" onSubmit={submitSearch}><Search size={16}/><input aria-label="Search features or coordinates" title="Search imported feature names or longitude,latitude. Use Real OSM discovery to resolve a location name." placeholder="Search imported features or lng, lat…" value={searchText} onChange={e=>setSearchText(e.target.value)}/><button type="submit" aria-label="Run search"><ArrowRight size={15}/></button></form>
            <label className="study-selector"><MapPin size={14}/><select aria-label="Study area" value={areaId} onChange={e=>selectArea(e.target.value)}>{studyAreas.map(a=><option value={a.id} key={a.id}>{a.name}</option>)}</select></label>
            <Button variant={filtersOpen?'default':'outline'} aria-expanded={filtersOpen} onClick={()=>setFiltersOpen(!filtersOpen)}><Filter size={14}/>Filters{filters.categories.length>0&&<span className="filter-count">{filters.categories.length}</span>}</Button>
            <Button variant="ghost" size="icon" aria-label="Refresh query" disabled={features.isFetching} onClick={()=>{features.refetch();allFeatures.refetch();health.refetch()}}><RefreshCw size={16} className={features.isFetching?'spin':''}/></Button>
          </div>
          {filtersOpen&&<form className="filter-panel" onSubmit={applyFilters}><div className="filter-panel-top"><h3>Query filters</h3><span>All selected categories are queried together.</span><Button variant="ghost" size="icon" aria-label="Close query filters" onClick={()=>setFiltersOpen(false)}><X size={16}/></Button></div><fieldset><legend>Categories</legend><div className="category-filters">{categories.map(c=><label key={c.id}><input type="checkbox" checked={filterCategories.includes(c.id)} onChange={()=>setFilterCategories(list=>list.includes(c.id)?list.filter(id=>id!==c.id):[...list,c.id])}/>{c.label}</label>)}</div></fieldset><div className="spatial-filters"><label>Custom bounds · west,south,east,north<input placeholder="101.2,2.7,101.9,3.4" value={customBbox} onChange={e=>setCustomBbox(e.target.value)}/></label><label>Radius center · longitude,latitude<input placeholder="101.55,3.12" value={radiusCenter} onChange={e=>setRadiusCenter(e.target.value)}/></label><label>Radius · km<input type="number" min="0.001" max="200" step="any" value={radiusKm} onChange={e=>setRadiusKm(e.target.value)}/></label></div><p className="filter-hint">A radius search overrides bounds and uses geodesic proximity. Clearing both uses the selected study extent.</p><div className="filter-footer"><Button variant="ghost" onClick={clearFilters}>Reset filters</Button><Button type="submit" disabled={filterCategories.length===0}><Check size={14}/>Apply filters</Button></div></form>}
          {formError&&<div className="query-error" role="alert">{formError}<button aria-label="Dismiss form error" onClick={()=>setFormError('')}><X size={14}/></button></div>}
          <div className="map-meta-toolbar"><div><span className="scope-chip"><i/>{scopeLabel}</span><span className="extent-note">{area.description}</span></div><div><span>{visibleCount??'—'} visible / {mapData?.meta.returned??'—'} mapped</span><button onClick={useMapExtent}>Search this map<ArrowRight size={12}/></button></div></div>
          {features.error&&<div className="query-error" role="alert"><TriangleAlert size={15}/>{features.error.message}{data?' Last successful results remain displayed.':''}<Button variant="outline" size="sm" onClick={()=>features.refetch()}>Retry</Button></div>}
          {!features.isFetching&&data?.meta.total===0&&<div className="query-empty" role="status">No matching records in this dataset and extent. This does not establish real-world absence.<button onClick={clearFilters}>Reset query filters</button></div>}
          {allFeatures.error&&<div className="query-error" role="alert">Map/export query failed: {allFeatures.error.message}<Button variant="outline" size="sm" onClick={()=>allFeatures.refetch()}>Retry map query</Button></div>}
          {mapData?.meta.has_more&&<div className="query-error" role="status">Map/export safety cap: showing {mapData.meta.returned} of {mapData.meta.total}. Narrow the query to display every match.</div>}
          <div className="gis-split"><div className="map-column"><MapWorkspace ref={map} data={mapData} initialBbox={area.bbox} onViewport={()=>{}} onLog={addLog}/>{(features.isFetching||allFeatures.isFetching)&&<div className="query-loading" role="status">Querying {mode==='fixture'?'synthetic fixture':'data source'}…</div>}</div><Inspector data={mapData} health={health.data} tab={inspectorTab} setTab={setInspectorTab}/></div>
          <AttributeTable data={data} expanded={tableOpen} setExpanded={setTableOpen} tab={tableTab} setTab={setTableTab} logs={logs} onSelect={chooseFeature} onPage={offset=>setFilters(f=>({...f,offset}))} busy={features.isFetching}/>
        </section>
        </>}
        <footer className="workspace-footer"><span><ShieldCheck size={12}/>Intelligent Industrial & Logistics Geospatial Intelligence</span><span>Phase 5 · {mode==='fixture'?'Synthetic dataset':'Data coverage applies'}<span className="footer-dot"/>EPSG:4326<a href={(apiBase||'http://127.0.0.1:8000')+'/docs'} target="_blank" rel="noreferrer"><CircleHelp size={13}/>API docs</a></span></footer>
      </main>
    </div>
  </div>
}
function RulerIcon(){return <Settings2 size={23}/>}
