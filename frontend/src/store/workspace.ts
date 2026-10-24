import type { Feature } from 'geojson'
import { create } from 'zustand'
import { categories, type CategoryId, type SpatialFeature, type Tool } from '../types'
interface Workspace {
  selected: SpatialFeature | null; setSelected: (feature: SpatialFeature | null) => void
  visible: CategoryId[]; toggleLayer: (id: CategoryId) => void
  order: CategoryId[]; moveLayer: (id: CategoryId, direction: -1 | 1) => void
  sketches: Feature[]; setSketches: (features:Feature[])=>void
  tool: Tool; setTool: (tool: Tool) => void
}
export const useWorkspace = create<Workspace>((set) => ({
  selected: null, setSelected: selected => set({ selected }),
  visible: categories.map(c => c.id),
  toggleLayer: id => set(state => ({ visible: state.visible.includes(id) ? state.visible.filter(c => c !== id) : [...state.visible, id] })),
  order: categories.map(c => c.id),
  moveLayer: (id, direction) => set(state => {
    const order = [...state.order], index = order.indexOf(id), next = index + direction
    if (next >= 0 && next < order.length) [order[index], order[next]] = [order[next], order[index]]
    return { order }
  }),
  sketches:[],setSketches:sketches=>set({sketches}),
  tool: 'select', setTool: tool => set({ tool }),
}))
