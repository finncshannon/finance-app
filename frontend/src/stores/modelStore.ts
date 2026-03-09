import { create } from 'zustand';
import { api } from '../services/api';
import type { AssumptionSet, SliderResult } from '../types/models';

export type ModelType = 'dcf' | 'ddm' | 'comps' | 'revenue_based';

interface ModelScore {
  model_type: string;
  score: number;
  applicable: boolean;
  reasoning: string;
}

interface ModelDetectionResult {
  ticker: string;
  recommended_model: string;
  confidence: string;
  confidence_percentage: number;
  scores: ModelScore[];
  characteristics: Record<string, boolean>;
}

interface ModelOutput {
  intrinsic_value_per_share: number;
  enterprise_value: number;
  equity_value: number;
  current_price: number;
  upside_downside_pct: number;
  calculation_duration_ms: number;
}

interface ModelVersion {
  id: number;
  version_number: number;
  annotation: string | null;
  created_at: string;
}

interface ModelState {
  activeTicker: string | null;
  activeModelType: ModelType | null;
  activeModelId: number | null;
  detectionResult: ModelDetectionResult | null;
  assumptions: Record<string, unknown>;
  assumptionData: AssumptionSet | null;
  assumptionOverrides: Record<string, number>;
  output: ModelOutput | null;
  versions: ModelVersion[];
  loading: boolean;
  isCalculating: boolean;
  pendingSliderOverrides: Record<string, number>;
  sensitivityParams: Record<string, unknown> | null;
  sliderOverrides: Record<string, number>;
  sliderResult: SliderResult | null;
  cachedModelResult: unknown;
  cachedModelMeta: { ticker: string; modelType: ModelType } | null;

  setTicker: (ticker: string) => void;
  setModelType: (type: ModelType) => void;
  setDetectionResult: (result: ModelDetectionResult | null) => void;
  setActiveModelId: (id: number | null) => void;
  setAssumptions: (assumptions: Record<string, unknown>) => void;
  updateAssumption: (key: string, value: unknown) => void;
  setAssumptionData: (data: AssumptionSet | null) => void;
  setAssumptionOverrides: (overrides: Record<string, number>) => void;
  setAssumptionOverride: (key: string, value: number) => void;
  clearAssumptionOverrides: () => void;
  setOutput: (output: ModelOutput | null) => void;
  setVersions: (versions: ModelVersion[]) => void;
  setLoading: (loading: boolean) => void;
  setIsCalculating: (calculating: boolean) => void;
  setPendingSliderOverride: (key: string, value: number) => void;
  pushSliderToAssumptions: () => void;
  pullAssumptionsToSliders: (assumptions: Record<string, number>) => void;
  clearSliderOverrides: () => void;
  setSensitivityParams: (params: Record<string, unknown> | null) => void;
  setSliderOverride: (key: string, value: number) => void;
  setSliderOverrides: (overrides: Record<string, number>) => void;
  setSliderResult: (result: SliderResult | null) => void;
  setCachedModelResult: (ticker: string, modelType: ModelType, result: unknown) => void;
  clearCachedModelResult: () => void;
  reset: () => void;
}

export const useModelStore = create<ModelState>((set) => ({
  activeTicker: null,
  activeModelType: null,
  activeModelId: null,
  detectionResult: null,
  assumptions: {},
  assumptionData: null,
  assumptionOverrides: {},
  output: null,
  versions: [],
  loading: false,
  isCalculating: false,
  pendingSliderOverrides: {},
  sensitivityParams: null,
  sliderOverrides: {},
  sliderResult: null,
  cachedModelResult: null,
  cachedModelMeta: null,

  setTicker: (ticker) => {
    set({ activeTicker: ticker.toUpperCase(), loading: true, detectionResult: null, assumptionData: null, assumptionOverrides: {}, cachedModelResult: null, cachedModelMeta: null });
    // Trigger detection in the background
    api
      .get<ModelDetectionResult>(`/api/v1/model-builder/${ticker.toUpperCase()}/detect`)
      .then((result) => {
        set({
          detectionResult: result,
          activeModelType: result.recommended_model as ModelType,
          loading: false,
        });
      })
      .catch(() => {
        set({ loading: false });
      });
  },

  setModelType: (type) => set({ activeModelType: type }),
  setDetectionResult: (result) => set({ detectionResult: result }),
  setActiveModelId: (id) => set({ activeModelId: id }),
  setAssumptions: (assumptions) => set({ assumptions }),
  updateAssumption: (key, value) =>
    set((state) => ({
      assumptions: { ...state.assumptions, [key]: value },
    })),
  setAssumptionData: (data) => set({ assumptionData: data }),
  setAssumptionOverrides: (overrides) => set({ assumptionOverrides: overrides }),
  setAssumptionOverride: (key, value) =>
    set((state) => ({
      assumptionOverrides: { ...state.assumptionOverrides, [key]: value },
    })),
  clearAssumptionOverrides: () => set({ assumptionOverrides: {} }),
  setOutput: (output) => set({ output }),
  setVersions: (versions) => set({ versions }),
  setLoading: (loading) => set({ loading }),
  setIsCalculating: (calculating) => set({ isCalculating: calculating }),

  setPendingSliderOverride: (key, value) =>
    set((state) => ({
      pendingSliderOverrides: { ...state.pendingSliderOverrides, [key]: value },
    })),

  pushSliderToAssumptions: () =>
    set((state) => ({
      assumptions: { ...state.assumptions, ...state.pendingSliderOverrides },
      pendingSliderOverrides: {},
    })),

  pullAssumptionsToSliders: (assumptions) =>
    set({ pendingSliderOverrides: assumptions }),

  clearSliderOverrides: () => set({ pendingSliderOverrides: {} }),

  setSensitivityParams: (params) => set({ sensitivityParams: params }),

  setSliderOverride: (key, value) =>
    set((state) => ({
      sliderOverrides: { ...state.sliderOverrides, [key]: value },
    })),
  setSliderOverrides: (overrides) => set({ sliderOverrides: overrides }),
  setSliderResult: (result) => set({ sliderResult: result }),

  setCachedModelResult: (ticker, modelType, result) =>
    set({ cachedModelResult: result, cachedModelMeta: { ticker, modelType } }),
  clearCachedModelResult: () => set({ cachedModelResult: null, cachedModelMeta: null }),

  reset: () =>
    set({
      activeTicker: null,
      activeModelType: null,
      activeModelId: null,
      detectionResult: null,
      assumptions: {},
      assumptionData: null,
      assumptionOverrides: {},
      output: null,
      versions: [],
      loading: false,
      isCalculating: false,
      pendingSliderOverrides: {},
      sensitivityParams: null,
      sliderOverrides: {},
      sliderResult: null,
      cachedModelResult: null,
      cachedModelMeta: null,
    }),
}));
