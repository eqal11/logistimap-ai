import { Activity, Boxes, Building2, ChartNoAxesCombined, ChevronRight, Database, Factory, Globe2, Layers, LayoutDashboard, LockKeyhole, Map, Network, Route, Settings2, Sparkles, Warehouse } from 'lucide-react'
import type {LucideIcon} from 'lucide-react'
const navigation: {id:string;label:string;icon:LucideIcon;phase?:number}[] = [
  {id:'dashboard',label:'Dashboard overview',icon:LayoutDashboard},
  {id:'explorer',label:'Industrial GIS Explorer',icon:Map},
  {id:'clusters',label:'Industrial Clusters',icon:Factory},
  {id:'routing',label:'Freight Route Planner',icon:Route},
  {id:'warehouses',label:'Warehouse Explorer',icon:Warehouse},
  {id:'sites',label:'Warehouse Site Selection',icon:Building2},
  {id:'accessibility',label:'Network Accessibility',icon:Network},
  {id:'industrial-accessibility',label:'Industrial Accessibility',icon:Building2},
  {id:'saved-analyses',label:'Saved Analyses',icon:Database},
  {id:'route-history',label:'Saved Route History',icon:Route},
  {id:'optimization',label:'Logistics Optimization',icon:Boxes},
  {id:'geoai',label:'GeoAI Copilot',icon:Sparkles},
  {id:'toolbox',label:'Spatial Analysis Toolbox',icon:Layers},
  {id:'reports',label:'Analytics & Reports',icon:ChartNoAxesCombined},
  {id:'data',label:'Data Management',icon:Database},
  {id:'settings',label:'Settings',icon:Settings2},
]
export const moduleInfo = Object.fromEntries(navigation.map(n=>[n.id,n]))
export function Sidebar({active,onNavigate,open}:{active:string;onNavigate:(id:string)=>void;open:boolean}){
  return <aside className={'sidebar '+(open?'sidebar-open':'')}>
    <a className="brand" href="#explorer" onClick={e=>{e.preventDefault();onNavigate('explorer')}}><div className="brand-mark"><Boxes size={24}/></div><span>LogistiMap<span className="brand-ai">AI</span><small>GEOSPATIAL INTELLIGENCE</small></span></a>
    <div className="workspace-label"><Globe2 size={14}/><span>Malaysia workspace</span><span className="version-tag">v0.7</span></div>
    <div className="nav-heading">WORKSPACE</div>
    <nav aria-label="Primary navigation">{navigation.map(({id,label,icon:Icon,phase})=><div key={id}>
      {id==='toolbox'&&<div className="nav-heading secondary">TOOLS & OPERATIONS</div>}
      <button className={'nav-item '+(active===id?'nav-active':'')} onClick={()=>onNavigate(id)} aria-current={active===id?'page':undefined} title={phase?label+' · unavailable until Phase '+phase:label}>
        <Icon size={17}/><span>{label}</span>{phase?<small className="phase-label">P{phase}</small>:active===id?<ChevronRight size={13}/>:null}
      </button>
    </div>)}</nav>
    <div className="sidebar-bottom"><div className="foundation-status"><Activity size={17}/><div><strong>Industrial spatial intelligence</strong><small>Phase 7 · GeoAI intelligence</small></div><i/></div><div className="local-user"><span className="avatar">LM</span><div><strong>Local workspace</strong><small><LockKeyhole size={10}/> Authentication unavailable</small></div></div></div>
  </aside>
}
