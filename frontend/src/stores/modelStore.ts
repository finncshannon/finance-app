import { create } from 'zustand';
import { api } from '../services/api';
import type { SliderResult } from '../types/models';

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
  output: ModelOutput | null;
  versions: ModelVersion[];
  loading: boolean;
  isCalculating: boolean;
  pendingSliderOverrides: Record<string, number>;
  sensitivityParams: Record<string, unknown> | null;
  sliderOverrides: Record<string, number>;
  sliderResult: SliderResult | null;

  setTicker: (ticker: string) => void;
  setModelType: (type: ModelType) => void;
  setDetectionResult: (result: ModelDetectionResult | null) => void;
  setActiveModelId: (id: number | null) => void;
  setAssumptions: (assumptions: Record<string, unknown>) => void;
  updateAssumption: (key: string, value: unknown) => void;
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
  reset: () => void;
}

export const useModelStore = create<ModelState>((set) => ({
  activeTicker: null,
  activeModelType: null,
  activeModelId: null,
  detectionResult: null,
  assumptions: {},
  output: null,
  versions: [],
  loading: false,
  isCalculating: false,
  pendingSliderOverrides: {},
  sensitivityParams: null,
  sliderOverrides: {},
  sliderResult: null,

  setTicker: (ticker) => {
    set({ activeTicker: ticker.toUpperCase(), loading: true, detectionResult: null });
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

  reset: () =>
    set({
      activeTicker: null,
      activeModelType: null,
      activeModelId: null,
      detectionResult: null,
      assumptions: {},
      output: null,
      versions: [],
      loading: false,
      isCalculating: false,
      pendingSliderOverrides: {},
      sensitivityParams: null,
      sliderOverrides: {},
      sliderResult: null,
    }),
}));
