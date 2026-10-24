import {create} from 'zustand'
import {newScenario,type Scenario,type OptimizationResult} from '../services/optimization'
interface State {scenario:Scenario;result:OptimizationResult|null;savedId:string|null;jobId:string|null;jobScenarioId:string|null;update:(scenario:Scenario)=>void;load:(scenario:Scenario,id:string|null,result?:OptimizationResult|null)=>void;setResult:(r:OptimizationResult)=>void;setJob:(id:string|null,scenarioId:string|null)=>void}
export const useOptimization=create<State>(set=>({scenario:newScenario(),result:null,savedId:null,jobId:null,jobScenarioId:null,
 update:scenario=>set({scenario,savedId:null,result:null}),
 load:(scenario,id,result=null)=>set({scenario,savedId:id,result}),
 setResult:result=>set({result}),
 setJob:(jobId,jobScenarioId)=>set({jobId,jobScenarioId})}))
