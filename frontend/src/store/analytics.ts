import {create} from 'zustand'
import type {AnalysisResult} from '../services/analytics'
export interface AnalysisLayer {id:string;result:AnalysisResult;visible:boolean;color:string}
interface State {layers:AnalysisLayer[];activeId:string|null;add:(r:AnalysisResult)=>void;toggle:(id:string)=>void;remove:(id:string)=>void;activate:(id:string)=>void}
const colors=['#0e9b87','#6366d8','#c8842b','#348cc6','#b86583']
export const useAnalyses=create<State>((set)=>({layers:[],activeId:null,
 add:result=>set(s=>{const id=result.saved_id??result.calculation_id??crypto.randomUUID();return {activeId:id,layers:[...s.layers.filter(l=>l.id!==id&&!(result.calculation_id&&l.result.calculation_id===result.calculation_id)),{id,result,visible:true,color:s.layers.find(l=>result.calculation_id&&l.result.calculation_id===result.calculation_id)?.color??colors[s.layers.length%colors.length]}].slice(-5)}}),
 toggle:id=>set(s=>({layers:s.layers.map(l=>l.id===id?{...l,visible:!l.visible}:l)})),
 remove:id=>set(s=>({layers:s.layers.filter(l=>l.id!==id),activeId:s.activeId===id?s.layers.find(l=>l.id!==id)?.id??null:s.activeId})),
 activate:id=>set({activeId:id})
}))
