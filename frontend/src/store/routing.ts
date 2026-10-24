import { create } from 'zustand'
import type { RouteResult, RouteStop, RoutingPoint } from '../types/routing'
interface RoutingState {
  stops:RouteStop[];result:RouteResult|null;activeRoute:number;pickId:string|null;revision:number;
  setPoint:(id:string,point:RoutingPoint|null)=>void;
  setEndpoint:(role:'origin'|'destination',point:RoutingPoint)=>void;
  addStop:()=>void;removeStop:(id:string)=>void;moveStop:(id:string,direction:-1|1)=>void;
  reverse:()=>void;reset:()=>void;setPick:(id:string|null)=>void;
  setResult:(result:RouteResult)=>void;setActiveRoute:(index:number)=>void
}
const blank=()=>[{id:'origin',point:null},{id:'destination',point:null}]
const invalidate={result:null,activeRoute:0,pickId:null}
export const useRouting=create<RoutingState>(set=>({
  stops:blank(),result:null,activeRoute:0,pickId:null,revision:0,
  setPoint:(id,point)=>set(s=>({...invalidate,stops:s.stops.map(p=>p.id===id?{...p,point}:p),revision:s.revision+1})),
  setEndpoint:(role,point)=>set(s=>({...invalidate,stops:s.stops.map((p,i)=>i===(role==='origin'?0:s.stops.length-1)?{...p,point}:p),revision:s.revision+1})),
  addStop:()=>set(s=>s.stops.length>=8?s:({...invalidate,stops:[...s.stops.slice(0,-1),{id:crypto.randomUUID(),point:null},s.stops.at(-1)!],revision:s.revision+1})),
  removeStop:id=>set(s=>({...invalidate,stops:s.stops.filter((p,i)=>i===0||i===s.stops.length-1||p.id!==id),revision:s.revision+1})),
  moveStop:(id,direction)=>set(s=>{
    const stops=[...s.stops],i=stops.findIndex(p=>p.id===id),next=i+direction
    if(i<=0||i>=stops.length-1||next<=0||next>=stops.length-1)return s
    ;[stops[i],stops[next]]=[stops[next],stops[i]]
    return {...invalidate,stops,revision:s.revision+1}
  }),
  reverse:()=>set(s=>({...invalidate,stops:[...s.stops].reverse(),revision:s.revision+1})),
  reset:()=>set(s=>({...invalidate,stops:blank(),revision:s.revision+1})),
  setPick:pickId=>set({pickId}),
  setResult:result=>set({result,activeRoute:0,pickId:null}),
  setActiveRoute:index=>set(s=>s.result?.routes[index]?{activeRoute:index}:s),
}))
