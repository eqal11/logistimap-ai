import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, Map as MapInstance, StyleSpecification } from 'maplibre-gl'
import type { Feature, FeatureCollection, Geometry, Position } from 'geojson'
import { Crosshair, Download, LocateFixed, MousePointer2, Plus, Minus, RotateCcw, MapPin, Spline, Pentagon, Ruler, Maximize, Check, Trash2, X } from 'lucide-react'
import { Button } from '../components/ui/button'
import { categories, type Bbox, type SearchResult, type Tool } from '../types'
import { useWorkspace } from '../store/workspace'
import { apiBase, downloadGeoJSON } from '../services/api'
import type { Coordinate, RouteResult } from '../types/routing'
import type { AnalysisLayer } from '../store/analytics'

export interface MapHandle {
  flyTo: (coordinates: [number, number]) => void
  fit: (bbox: Bbox) => void
  getBounds: () => Bbox | undefined
}
interface Props {
  data?: SearchResult; initialBbox:Bbox; onViewport:(bbox:Bbox)=>void;onLog:(message:string)=>void;
  analysisLayers?:AnalysisLayer[];analysisHeatmap?:boolean;onAnalysisSelect?:(f:Feature<Geometry>)=>void;
  geoaiSelection?:Feature;geoaiTop?:FeatureCollection;
  siteData?:FeatureCollection;selectedSite?:string;onSiteSelect?:(f:Feature)=>void;
  optimizationData?:FeatureCollection;selectedOptimizationVehicle?:string;onOptimizationSelect?:(f:Feature)=>void;
  routingResult?:RouteResult;activeRoute?:number;
  routeStops?:{coordinates:Coordinate;label:string;name:string}[];
  pickingRoutePoint?:boolean;onRoutePoint?:(coordinates:Coordinate)=>void;onRouteSelect?:(index:number)=>void
}
const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }
const OFFLINE: StyleSpecification = { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#e8eeee' } }] }
const layerIds = (id: string) => ['fill', 'line', 'point'].map(kind => id + '-' + kind)
function addGeometryLayers(map: MapInstance, source: string, color: string, highlight = false) {
  if (!map.getSource(source)) map.addSource(source, { type: 'geojson', data: EMPTY })
  if (map.getLayer(source + '-point')) return
  map.addLayer({ id: source + '-fill', type: 'fill', source, filter: ['==', ['geometry-type'], 'Polygon'], paint: { 'fill-color': color, 'fill-opacity': highlight ? 0.23 : 0.14 } })
  map.addLayer({ id: source + '-line', type: 'line', source, filter: ['!=', ['geometry-type'], 'Point'], paint: { 'line-color': color, 'line-width': highlight ? 4 : 2 } })
  map.addLayer({ id: source + '-point', type: 'circle', source, filter: ['==', ['geometry-type'], 'Point'], paint: { 'circle-color': color, 'circle-radius': highlight ? 11 : 7, 'circle-stroke-width': highlight ? 3 : 2, 'circle-stroke-color': '#ffffff', 'circle-opacity': highlight ? 0.65 : 1 } })
}
export const MapWorkspace = forwardRef<MapHandle, Props>(function MapWorkspace(props, ref) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapInstance | null>(null)
  const latest = useRef(props); latest.current = props
  const selected = useWorkspace(s => s.selected), visible = useWorkspace(s => s.visible), order = useWorkspace(s => s.order)
  const tool = useWorkspace(s => s.tool), setTool = useWorkspace(s => s.setTool)
  const points = useRef<Position[]>([]), sketches = useRef<Feature[]>(useWorkspace.getState().sketches)
  const [draftCount, setDraftCount] = useState(0), [drawCount, setDrawCount] = useState(sketches.current.length)
  const [measurement, setMeasurement] = useState(()=>{const last=sketches.current.at(-1);return last?(last.geometry.type==='Polygon'?Number(last.properties?.area_sq_km??0).toFixed(3)+' km²':Number(last.properties?.length_km??0).toFixed(3)+' km')+' · WGS84 geodesic':''}), [busy, setBusy] = useState(false)
  const [mapReady, setMapReady] = useState(false), [styleVersion, setStyleVersion] = useState(0)
  const [basemap, setBasemap] = useState('positron'), [coords, setCoords] = useState('101.55000°, 3.12000°')
  const [error, setError] = useState(''), [tileError, setTileError] = useState(false), [initializing, setInitializing] = useState(true)
  const popup = useRef<maplibregl.Popup | null>(null)
  const getBbox = (map: MapInstance): Bbox => {
    const b = map.getBounds()
    return [Math.max(-180,b.getWest()),Math.max(-90,b.getSouth()),Math.min(180,b.getEast()),Math.min(90,b.getNorth())]
  }
  useImperativeHandle(ref, () => ({
    flyTo: coordinates => mapRef.current?.flyTo({ center: coordinates, zoom: 12 }),
    fit: bbox => mapRef.current?.fitBounds([[bbox[0],bbox[1]],[bbox[2],bbox[3]]], { padding: 60, duration: 800 }),
    getBounds: () => mapRef.current ? getBbox(mapRef.current) : undefined,
  }), [])
  useEffect(()=>{const map=mapRef.current;if(!map||!mapReady)return;addGeometryLayers(map,'geoai-top','#d29723',true);(map.getSource('geoai-top') as GeoJSONSource)?.setData(props.geoaiTop??EMPTY)},[props.geoaiTop,mapReady,styleVersion])
  useEffect(()=>{const map=mapRef.current;if(!map||!mapReady)return;addGeometryLayers(map,'geoai-highlight','#e39a23',true);(map.getSource('geoai-highlight') as GeoJSONSource)?.setData({type:'FeatureCollection',features:props.geoaiSelection?[props.geoaiSelection]:[]})},[props.geoaiSelection,mapReady,styleVersion])
  useEffect(() => {
    if (!container.current) return
    let map: MapInstance
    try {
      map = new maplibregl.Map({
        container: container.current, style: 'https://tiles.openfreemap.org/styles/positron',
        bounds: [[props.initialBbox[0],props.initialBbox[1]],[props.initialBbox[2],props.initialBbox[3]]],
        fitBoundsOptions: { padding: 42 }, attributionControl: { compact: true },
        maxZoom: 18, minZoom: 2, renderWorldCopies: false,
      })
    } catch {
      setError('WebGL unavailable. Feature table, API queries and exports remain usable.'); setInitializing(false); return
    }
    mapRef.current = map
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric', maxWidth: 120 }), 'bottom-left')
    map.doubleClickZoom.disable()
    map.on('style.load', () => {
      setMapReady(true); setInitializing(false); setTileError(false); setStyleVersion(v=>v+1)
      latest.current.onViewport(getBbox(map))
    })
    map.on('error', () => { setTileError(true); setInitializing(false) })
    map.on('moveend', () => latest.current.onViewport(getBbox(map)))
    map.on('mousemove', e => setCoords(e.lngLat.lng.toFixed(5)+'°, '+e.lngLat.lat.toFixed(5)+'°'))
    map.on('click', event => {
      const current = useWorkspace.getState()
      if(latest.current.pickingRoutePoint){latest.current.onRoutePoint?.([event.lngLat.lng,event.lngLat.lat]);return}
      if(latest.current.siteData&&current.tool==='select'){
        const layers=['site-points','site-fills','site-lines'].filter(id=>map.getLayer(id))
        const hit=layers.length?map.queryRenderedFeatures(event.point,{layers})[0]:undefined
        if(hit){latest.current.onSiteSelect?.({type:'Feature',id:hit.id,geometry:hit.geometry as Geometry,properties:hit.properties});popup.current?.remove();const node=document.createElement('div');node.textContent=String(hit.properties?.name??'Candidate')+' · score '+String(hit.properties?.score??'not evaluated')+' · candidate suitability, not development approval';popup.current=new maplibregl.Popup({offset:10}).setLngLat(event.lngLat).setDOMContent(node).addTo(map);return}
      }
      if(latest.current.optimizationData&&current.tool==='select'){
        const ids=['optimization-lines','optimization-points'].filter(id=>map.getLayer(id))
        const hit=ids.length?map.queryRenderedFeatures([[event.point.x-5,event.point.y-5],[event.point.x+5,event.point.y+5]],{layers:ids})[0]:undefined
        if(hit){latest.current.onOptimizationSelect?.({type:'Feature',id:hit.id,geometry:hit.geometry as Geometry,properties:hit.properties});popup.current?.remove();const node=document.createElement('div');node.textContent=(hit.properties?.scenario_name?String(hit.properties.scenario_label)+': '+String(hit.properties.scenario_name)+' · ':'')+String(hit.properties?.vehicle??hit.properties?.name??'Candidate reference')+' · '+String(hit.properties?.distance_m??'')+(hit.properties?.distance_m?' m final road route':'');popup.current=new maplibregl.Popup({offset:10}).setLngLat(event.lngLat).setDOMContent(node).addTo(map);return}
      }
      if(latest.current.routingResult&&current.tool==='select'){
        const routeLayers=['route-main','route-alternatives'].filter(id=>map.getLayer(id))
        const hit=routeLayers.length?map.queryRenderedFeatures(event.point,{layers:routeLayers})[0]:undefined
        if(hit){latest.current.onRouteSelect?.(Number(hit.properties?.route_index??0));return}
      }
      if(current.tool==='select'&&latest.current.analysisLayers?.length){
        const ids=latest.current.analysisLayers.filter(l=>l.visible).flatMap(l=>['fill','line','point'].map(k=>'analysis-'+l.id+'-'+k)).filter(id=>map.getLayer(id))
        const hit=ids.length?map.queryRenderedFeatures([[event.point.x-4,event.point.y-4],[event.point.x+4,event.point.y+4]],{layers:ids})[0]:undefined
        if(hit){latest.current.onAnalysisSelect?.({type:'Feature',id:hit.id,geometry:hit.geometry as Geometry,properties:hit.properties});return}
      }
      if (current.tool !== 'select') {
        popup.current?.remove(); const coordinate=[event.lngLat.lng,event.lngLat.lat]; if(current.tool==='point') points.current=[coordinate]; else points.current.push(coordinate); setDraftCount(points.current.length)
        const draft: Feature = { type: 'Feature', properties: { name: 'Draft sketch' }, geometry: points.current.length>1 ? { type:'LineString',coordinates:points.current } : { type:'Point',coordinates:points.current[0] } }
        ;(map.getSource('sketch') as GeoJSONSource | undefined)?.setData({type:'FeatureCollection',features:[...sketches.current,draft]})
        return
      }
      try {
      const layers = current.order.flatMap(id=>layerIds('cat-'+id)).filter(id=>map.getLayer(id))
      const hits = map.queryRenderedFeatures([[event.point.x-5,event.point.y-5],[event.point.x+5,event.point.y+5]],{layers})
      const feature = latest.current.data?.features.find(f=>f.id===String(hits[0]?.properties?.__feature_id ?? hits[0]?.id))
      if (!feature) { current.setSelected(null); popup.current?.remove(); return }
      current.setSelected(feature); popup.current?.remove()
      const node=document.createElement('div'), label=document.createElement('strong'), detail=document.createElement('p')
      label.textContent=feature.properties.name; detail.textContent=feature.properties.synthetic?'Synthetic test feature · select in inspector':feature.properties.source
      node.append(label,detail)
      popup.current=new maplibregl.Popup({offset:12,maxWidth:'280px'}).setLngLat(event.lngLat).setDOMContent(node).addTo(map)
      } catch(err) { setError('Selection unavailable: '+(err instanceof Error?err.message:'map style is loading')) }
    })
    const observer=new ResizeObserver(()=>map.resize()); observer.observe(container.current)
    return ()=>{observer.disconnect();popup.current?.remove();map.remove();mapRef.current=null}
  // Lifecycle uses latest refs to avoid resetting map on every query.
  }, [])
  useEffect(()=>{
    const map=mapRef.current
    if(!mapReady || !map) return
    categories.forEach(category=>{
      const source='cat-'+category.id
      addGeometryLayers(map,source,category.color)
      const data=(props.data?.features??[]).filter(f=>f.properties.categories.find(id=>visible.includes(id))===category.id).map(f=>({...f,properties:{...f.properties,__feature_id:f.id}}))
      ;(map.getSource(source) as GeoJSONSource).setData({type:'FeatureCollection',features:data})
    })
    ;[...order].reverse().forEach(id=>layerIds('cat-'+id).forEach(layer=>map.moveLayer(layer)))
    addGeometryLayers(map,'selection','#0bba9d',true)
    ;(map.getSource('selection') as GeoJSONSource).setData({type:'FeatureCollection',features:selected?[selected]:[]})
    layerIds('selection').forEach(id=>map.moveLayer(id))
    addGeometryLayers(map,'sketch','#d06c3d')
    ;(map.getSource('sketch') as GeoJSONSource).setData({type:'FeatureCollection',features:sketches.current})
    layerIds('sketch').forEach(id=>map.moveLayer(id))
  },[props.data,selected,visible,order,mapReady,styleVersion])
  useEffect(()=>{
    const map=mapRef.current
    if(!mapReady||!map)return
    const sources=['road-routes','route-input-stops','route-road-snaps']
    sources.forEach(id=>{if(!map.getSource(id))map.addSource(id,{type:'geojson',data:EMPTY})})
    const routes:FeatureCollection={type:'FeatureCollection',features:(props.routingResult?.routes??[]).map(r=>({type:'Feature',id:'route-'+r.index,geometry:r.geometry,properties:{route_index:r.index,active:r.index===(props.activeRoute??0)}}))}
    ;(map.getSource('road-routes') as GeoJSONSource).setData(routes)
    const stops:FeatureCollection={type:'FeatureCollection',features:(props.routeStops??[]).map((s,i)=>({type:'Feature',id:'route-stop-'+i,geometry:{type:'Point',coordinates:s.coordinates},properties:{label:s.label,name:s.name}}))}
    ;(map.getSource('route-input-stops') as GeoJSONSource).setData(stops)
    ;(map.getSource('route-road-snaps') as GeoJSONSource).setData({type:'FeatureCollection',features:(props.routingResult?.waypoints??[]).map((p,i)=>({type:'Feature',id:'snap-'+i,geometry:{type:'Point',coordinates:p.snapped_coordinates},properties:{}}))})
    if(!map.getLayer('route-main')){
      map.addLayer({id:'route-alternatives',type:'line',source:'road-routes',filter:['==',['get','active'],false],paint:{'line-color':'#8796b8','line-width':4,'line-opacity':.8}})
      map.addLayer({id:'route-casing',type:'line',source:'road-routes',filter:['==',['get','active'],true],paint:{'line-color':'#ffffff','line-width':9}})
      map.addLayer({id:'route-main',type:'line',source:'road-routes',filter:['==',['get','active'],true],layout:{'line-join':'round','line-cap':'round'},paint:{'line-color':'#435ed7','line-width':5}})
      map.addLayer({id:'route-snaps',type:'circle',source:'route-road-snaps',paint:{'circle-radius':4,'circle-color':'#fff','circle-stroke-color':'#435ed7','circle-stroke-width':2}})
      map.addLayer({id:'route-markers',type:'circle',source:'route-input-stops',paint:{'circle-radius':12,'circle-color':'#223c71','circle-stroke-color':'#fff','circle-stroke-width':3}})
      if(basemap!=='minimal')map.addLayer({id:'route-marker-labels',type:'symbol',source:'route-input-stops',layout:{'text-field':['get','label'],'text-font':['Noto Sans Regular'],'text-size':11,'text-allow-overlap':true},paint:{'text-color':'#ffffff'}})
    }
    ;['route-alternatives','route-casing','route-main','route-snaps','route-markers','route-marker-labels'].forEach(id=>{if(map.getLayer(id))map.moveLayer(id)})
  },[props.routingResult,props.activeRoute,props.routeStops,props.data,visible,order,mapReady,styleVersion])
  const analysisSources=useRef<string[]>([])
  useEffect(()=>{
    const map=mapRef.current
    if(!mapReady||!map)return
    const wanted=(props.analysisLayers??[]).map(l=>'analysis-'+l.id)
    analysisSources.current.filter(id=>!wanted.includes(id)).forEach(id=>{
      [...layerIds(id),id+'-heat'].forEach(layer=>{if(map.getLayer(layer))map.removeLayer(layer)})
      if(map.getSource(id))map.removeSource(id)
    })
    analysisSources.current=wanted
    ;(props.analysisLayers??[]).forEach(layer=>{
      const source='analysis-'+layer.id
      addGeometryLayers(map,source,layer.color)
      ;(map.getSource(source) as GeoJSONSource).setData({type:'FeatureCollection',features:layer.result.features})
      const color:maplibregl.ExpressionSpecification=['case',['has','cluster_id'],
        ['match',['%', ['to-number',['get','cluster_id']],5],0,'#118b79',1,'#6366d8',2,'#c78325',3,'#2888c5',4,'#b65b83','#8a96a3'],
        ['has','density_per_km2'],['interpolate',['linear'],['to-number',['get','density_per_km2']],0,'#e0f3e9',2,'#75c7a1',10,'#0f937d',50,'#235587'],layer.color]
      map.setPaintProperty(source+'-fill','fill-color',color)
      map.setPaintProperty(source+'-fill','fill-opacity',.35)
      map.setPaintProperty(source+'-point','circle-color',color)
      map.setPaintProperty(source+'-point','circle-radius',5)
      if(!map.getLayer(source+'-heat'))map.addLayer({id:source+'-heat',type:'heatmap',source,
        filter:['in',['get','role'],['literal',['density_point','cluster_point']]],
        paint:{'heatmap-radius':32,'heatmap-intensity':.8,'heatmap-opacity':.75}})
      layerIds(source).forEach(id=>{map.setLayoutProperty(id,'visibility',layer.visible?'visible':'none');map.moveLayer(id)})
      map.setLayoutProperty(source+'-heat','visibility',layer.visible&&props.analysisHeatmap?'visible':'none')
      map.moveLayer(source+'-heat')
    })
  },[props.analysisLayers,props.analysisHeatmap,props.data,visible,order,selected,mapReady,styleVersion])
  useEffect(()=>{
    points.current=[];setDraftCount(0)
    mapRef.current?.getCanvas().style.setProperty('cursor',tool==='select'?'grab':'crosshair')
    ;(mapRef.current?.getSource('sketch') as GeoJSONSource|undefined)?.setData({type:'FeatureCollection',features:sketches.current})
  },[tool])
  useEffect(()=>{
    const map=mapRef.current;if(!mapReady||!map||!props.optimizationData)return
    if(!map.getSource('optimization'))map.addSource('optimization',{type:'geojson',data:EMPTY})
    ;(map.getSource('optimization') as GeoJSONSource).setData(props.optimizationData??EMPTY)
    if(!map.getLayer('optimization-lines')){
      map.addLayer({id:'optimization-casing',type:'line',source:'optimization',filter:['!=',['geometry-type'],'Point'],paint:{'line-color':'#fff','line-width':['case',['has','scenario_id'],5,8],'line-opacity':.8,'line-offset':['coalesce',['get','line_offset'],0]}})
      map.addLayer({id:'optimization-lines',type:'line',source:'optimization',filter:['!=',['geometry-type'],'Point'],layout:{'line-join':'round','line-cap':'round'},paint:{'line-color':['coalesce',['get','color'],'#087f80'],'line-width':4,'line-offset':['coalesce',['get','line_offset'],0],'line-dasharray':['match',['get','dash_index'],1,['literal',[4,2]],2,['literal',[1,2]],3,['literal',[6,2,1,2]],4,['literal',[8,3]],5,['literal',[3,2,1,2]],['literal',[1,0]]]}})
      map.addLayer({id:'optimization-points',type:'circle',source:'optimization',filter:['==',['geometry-type'],'Point'],paint:{'circle-color':['coalesce',['get','color'],'#087f80'],'circle-radius':11,'circle-stroke-width':2,'circle-stroke-color':'#fff'}})
    }
    map.setPaintProperty('optimization-lines','line-width',['case',['==',['get','vehicle_id'],props.selectedOptimizationVehicle??''],6,3])
    map.setPaintProperty('optimization-lines','line-opacity',['case',['==',['get','vehicle_id'],props.selectedOptimizationVehicle??''],1,.7])
    if(map.getStyle().glyphs&&!map.getLayer('optimization-labels')){
      map.addLayer({id:'optimization-arrows',type:'symbol',source:'optimization',filter:['!=',['geometry-type'],'Point'],layout:{'symbol-placement':'line','symbol-spacing':110,'text-field':'›','text-size':24,'text-allow-overlap':true,'text-font':['Noto Sans Regular'],'text-keep-upright':false,'text-offset':['match',['get','scenario_label'],'B',['literal',[0,.2083]],'C',['literal',[0,.4167]],'D',['literal',[0,.625]],['literal',[0,0]]]},paint:{'text-color':'#fff','text-halo-color':['coalesce',['get','color'],'#087f80'],'text-halo-width':1}})
      map.addLayer({id:'optimization-labels',type:'symbol',source:'optimization',filter:['==',['geometry-type'],'Point'],layout:{'text-field':['get','label'],'text-size':11,'text-font':['Noto Sans Regular'],'text-allow-overlap':true},paint:{'text-color':'#fff'}})
    }
  },[props.optimizationData,props.selectedOptimizationVehicle,mapReady,styleVersion])
  useEffect(()=>{
    const map=mapRef.current;if(!mapReady||!map||!props.siteData)return
    if(!map.getSource('site-suitability'))map.addSource('site-suitability',{type:'geojson',data:EMPTY})
    ;(map.getSource('site-suitability') as GeoJSONSource).setData(props.siteData)
    if(!map.getLayer('site-fills')){
      map.addLayer({id:'site-fills',type:'fill',source:'site-suitability',filter:['==',['geometry-type'],'Polygon'],paint:{'fill-color':['coalesce',['get','color'],'#89949b'],'fill-opacity':.35}})
      map.addLayer({id:'site-lines',type:'line',source:'site-suitability',filter:['!=',['geometry-type'],'Point'],paint:{'line-color':['coalesce',['get','color'],'#89949b'],'line-width':2}})
      map.addLayer({id:'site-points',type:'circle',source:'site-suitability',filter:['==',['geometry-type'],'Point'],paint:{'circle-color':['coalesce',['get','color'],'#89949b'],'circle-radius':11,'circle-stroke-color':'#fff','circle-stroke-width':2}})
    }
    map.setPaintProperty('site-lines','line-width',['case',['==',['get','candidate_id'],props.selectedSite??''],5,2])
    map.setPaintProperty('site-points','circle-stroke-width',['case',['==',['get','candidate_id'],props.selectedSite??''],4,2])
    if(map.getStyle().glyphs&&!map.getLayer('site-labels'))map.addLayer({id:'site-labels',type:'symbol',source:'site-suitability',filter:['==',['geometry-type'],'Point'],layout:{'text-field':['to-string',['coalesce',['get','rank'],'?']],'text-font':['Noto Sans Regular'],'text-size':11,'text-allow-overlap':true},paint:{'text-color':'#fff'}})
  },[props.siteData,props.selectedSite,mapReady,styleVersion])
  async function finishSketch(){
    if(busy)return
    const mode=useWorkspace.getState().tool, minimum=mode==='point'?1:['polygon','area'].includes(mode)?3:2
    if(points.current.length<minimum){setError('Add at least '+minimum+' map point(s).');return}
    const positions=points.current.map(p=>[...p])
    const geometry:Geometry=mode==='point'?{type:'Point',coordinates:positions[0]}:['polygon','area'].includes(mode)?{type:'Polygon',coordinates:[[...positions,positions[0]]]}:{type:'LineString',coordinates:positions}
    setBusy(true);setError('')
    try{
      const response=await fetch(apiBase+'/api/spatial/measure',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({geometry,crs:'EPSG:4326'}),signal:AbortSignal.timeout(15000)})
      const body=await response.json()
      if(!response.ok)throw new Error(body.error?.details?.[0]?.message??body.error?.message??'Invalid sketch geometry')
      const result=body.data as {length_km:number;area_sq_km:number}
      const label=['area','polygon'].includes(mode)?result.area_sq_km.toFixed(3)+' km²':result.length_km.toFixed(3)+' km'
      setMeasurement(label+' · WGS84 geodesic')
      const sketch:Feature={type:'Feature',id:'sketch-'+crypto.randomUUID(),properties:{name:'User sketch '+(sketches.current.length+1),source:'User drawn — unverified',crs:'EPSG:4326',...result},geometry}
      sketches.current=[...sketches.current,sketch];useWorkspace.getState().setSketches(sketches.current);points.current=[];setDraftCount(0);setDrawCount(sketches.current.length)
      ;(mapRef.current?.getSource('sketch') as GeoJSONSource)?.setData({type:'FeatureCollection',features:sketches.current})
      latest.current.onLog('Validated user sketch · '+label+' · not a road-network result.');setTool('select')
    }catch(err){setError(err instanceof Error?err.message:'Sketch validation failed')}
    finally{setBusy(false)}
  }
  function changeBasemap(value:string){
    setBasemap(value);setMapReady(false);setTileError(false)
    mapRef.current?.setStyle(value==='minimal'?OFFLINE:'https://tiles.openfreemap.org/styles/'+value, {diff:false})
  }
  function geolocate(){
    if(!navigator.geolocation){setError('Geolocation unsupported by this browser.');return}
    navigator.geolocation.getCurrentPosition(p=>{
      mapRef.current?.flyTo({center:[p.coords.longitude,p.coords.latitude],zoom:12})
      latest.current.onLog('Map moved to browser location. Location is not stored.')
    },err=>setError('Location unavailable: '+err.message),{timeout:10000})
  }
  useEffect(()=>{mapRef.current?.getCanvas().style.setProperty('cursor',props.pickingRoutePoint?'crosshair':tool==='select'?'grab':'crosshair')},[props.pickingRoutePoint,tool])
  const tools:{id:Tool;icon:typeof MousePointer2;label:string}[]=[
    {id:'select',icon:MousePointer2,label:'Select features'},{id:'point',icon:MapPin,label:'Draw point'},
    {id:'line',icon:Spline,label:'Draw line'},{id:'polygon',icon:Pentagon,label:'Draw polygon'},
    {id:'distance',icon:Ruler,label:'Measure distance'},{id:'area',icon:Maximize,label:'Measure area'},
  ]
  return <div className="map-workspace" aria-label="Interactive GIS workspace">
    <div ref={container} className="map-canvas" role="region" aria-label="Malaysia interactive map"/>
    <div className="map-heading"><span className="live-dot"/> SPATIAL WORKSPACE <span className="map-heading-divider"/><span>2D</span></div>
    <div className="map-tools" role="toolbar" aria-label="Map drawing tools">
      {tools.map(({id,icon:Icon,label})=><Button key={id} variant="ghost" size="icon" title={label} aria-label={label} aria-pressed={tool===id} className={tool===id?'active-tool':''} onClick={()=>{setError('');setTool(id)}}><Icon size={17}/></Button>)}
      <span className="toolbar-divider"/>
      <Button variant="ghost" size="icon" title="Use my location" aria-label="Use my location" onClick={geolocate}><LocateFixed size={18}/></Button>
      <Button variant="ghost" size="icon" title="Reset map" aria-label="Reset map" onClick={()=>mapRef.current?.fitBounds([[props.initialBbox[0],props.initialBbox[1]],[props.initialBbox[2],props.initialBbox[3]]],{padding:42})}><RotateCcw size={17}/></Button>
    </div>
    <div className="zoom-tools"><Button variant="ghost" size="icon" aria-label="Zoom in" onClick={()=>mapRef.current?.zoomIn()}><Plus size={18}/></Button><Button variant="ghost" size="icon" aria-label="Zoom out" onClick={()=>mapRef.current?.zoomOut()}><Minus size={18}/></Button></div>
    <div className="basemap-switch"><label><Crosshair size={14}/><select aria-label="Basemap" value={basemap} onChange={e=>changeBasemap(e.target.value)}><option value="positron">Light basemap</option><option value="dark">Dark basemap</option><option value="minimal">Minimal · no basemap</option></select></label></div>
    {initializing&&<div className="map-notice">Loading map style…</div>}
    {tileError&&<div className="map-notice warning">Basemap unavailable. <button onClick={()=>changeBasemap('minimal')}>Use minimal background</button></div>}
    {tool!=='select'&&<div className="draw-prompt"><span>Click map to add vertices · {draftCount} added</span><Button size="sm" onClick={finishSketch} disabled={busy}><Check size={13}/>{busy?'Validating…':'Finish'}</Button><Button size="icon" variant="ghost" aria-label="Cancel drawing" onClick={()=>setTool('select')}><X size={15}/></Button></div>}
    {error&&<div className="map-notice error" role="alert">{error}<button aria-label="Dismiss map error" onClick={()=>setError('')}><X size={14}/></button></div>}
    {drawCount>0&&<div className="sketch-summary"><span>{drawCount} user sketch{drawCount>1?'es':''} · {measurement}</span><Button variant="ghost" size="icon" aria-label="Export user sketches" onClick={()=>downloadGeoJSON({type:'FeatureCollection',features:sketches.current},'logistimap-user-sketches.geojson')}><Download size={14}/></Button><Button variant="ghost" size="icon" aria-label="Clear user sketches" onClick={()=>{sketches.current=[];useWorkspace.getState().setSketches([]);setDrawCount(0);(mapRef.current?.getSource('sketch') as GeoJSONSource)?.setData(EMPTY)}}><Trash2 size={14}/></Button></div>}
    <div className="coordinates">{coords}<span>WGS 84 · EPSG:4326</span></div>
    <div className="map-legend">{categories.filter(c=>visible.includes(c.id)&&props.data?.features.some(f=>f.properties.categories.includes(c.id))).map(c=><span key={c.id}><i style={{background:c.color}}/>{c.short}</span>)}</div>
  </div>
})
