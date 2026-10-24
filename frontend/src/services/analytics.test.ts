import {beforeEach,it,expect,vi} from 'vitest'
import {csvText,analyze,archiveSaved} from './analytics'
import {useAnalyses} from '../store/analytics'
beforeEach(()=>{vi.unstubAllGlobals();useAnalyses.setState({layers:[],activeId:null})})
it('escapes CSV quotes, commas, newlines and spreadsheet formula injection',()=>{
 const text=csvText([{name:'=SUM(1,2)',note:'a"b\nc',value:12},{name:'@cmd',note:null,value:0}])
 expect(text).toContain(`"'=SUM(1,2)"`);expect(text).toContain('"a""b\nc"');expect(text).toContain(`"'@cmd"`)
})
it('sends strict JSON operation and confirmed archive body',async()=>{
 const fetch=vi.fn().mockResolvedValue({ok:true,json:async()=>({})});vi.stubGlobal('fetch',fetch)
 await analyze({operation:'buffer',distance_m:1000})
 expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({operation:'buffer',distance_m:1000})
 await archiveSaved('analyses','saved-test')
 expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({confirmed:true})
})
it('keeps at most five separate result layers and preserves visibility',()=>{
 for(let i=0;i<6;i++)useAnalyses.getState().add({calculation_id:String(i),title:String(i)} as never)
 expect(useAnalyses.getState().layers.map(l=>l.id)).toEqual(['1','2','3','4','5'])
 useAnalyses.getState().toggle('3');expect(useAnalyses.getState().layers.find(l=>l.id==='3')?.visible).toBe(false)
 useAnalyses.getState().remove('5');expect(useAnalyses.getState().activeId).not.toBe('5')
})
