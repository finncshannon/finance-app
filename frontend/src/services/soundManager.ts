// Sound Manager — procedural Web Audio API sounds for boot sequence
// All methods are no-ops when sound is disabled or AudioContext unavailable

import { useSettingsStore } from '../stores/settingsStore';

let audioCtx: AudioContext | null = null;

function isSoundEnabled(): boolean {
  return useSettingsStore.getState().settings.sound_enabled !== 'false';
}

function ensureContext(): AudioContext | null {
  if (!audioCtx) return null;
  if (audioCtx.state === 'suspended') {
    audioCtx.resume();
  }
  return audioCtx;
}

export const soundManager = {
  initAudioContext() {
    if (!audioCtx) {
      try {
        audioCtx = new AudioContext();
      } catch {
        /* Web Audio not supported */
      }
    }
  },

  playBootTick() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;
    // Short 800Hz sine click, ~50ms
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 800;
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.05);
  },

  playBootComplete() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;
    // Ascending two-note tone: 600Hz → 900Hz, ~200ms
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(600, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(900, ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.1, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.2);
  },

  playStartupTone() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;
    // Layered chord swell: 440Hz + 554Hz + 660Hz, ~400ms
    [440, 554, 660].forEach((freq) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.001, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.1);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.4);
    });
  },
};
