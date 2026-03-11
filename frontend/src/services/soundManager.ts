// Sound Manager — procedural Web Audio API sounds
// Holographic boot hum engine + UI sounds

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

// Master gain — single control point for all engine layers
let engineMaster: GainNode | null = null;
let engineNodes: OscillatorNode[] = [];
let noiseSources: AudioBufferSourceNode[] = [];
let fadeStarted = false;

/** Create a white noise AudioBuffer */
function createNoiseBuffer(ctx: AudioContext, seconds: number): AudioBuffer {
  const sampleRate = ctx.sampleRate;
  const length = sampleRate * seconds;
  const buffer = ctx.createBuffer(1, length, sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) {
    data[i] = Math.random() * 2 - 1;
  }
  return buffer;
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

  /** Start the turbine spool-up — all layers route through engineMaster */
  startBootHum() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const t = ctx.currentTime;
    const spoolDuration = 8;
    fadeStarted = false;

    // Master gain — single fade point for all engine sound
    engineMaster = ctx.createGain();
    engineMaster.gain.setValueAtTime(1.0, t);
    engineMaster.connect(ctx.destination);

    const dest = engineMaster; // all layers connect here

    const noiseBuf = createNoiseBuffer(ctx, spoolDuration + 20);

    // Helper to create and track an oscillator layer
    const osc = (type: OscillatorType, freq: number, freqEnd: number, vol: number, volEnd: number) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = type;
      o.frequency.setValueAtTime(freq, t);
      o.frequency.exponentialRampToValueAtTime(freqEnd, t + spoolDuration);
      g.gain.setValueAtTime(vol, t);
      g.gain.linearRampToValueAtTime(volEnd, t + spoolDuration);
      o.connect(g).connect(dest);
      o.start(t);
      engineNodes.push(o);
    };

    // Helper for noise layers
    const noise = (filterType: BiquadFilterType, fStart: number, fEnd: number, q: number, vol: number, volEnd: number) => {
      const src = ctx.createBufferSource();
      src.buffer = noiseBuf;
      const f = ctx.createBiquadFilter();
      f.type = filterType;
      f.frequency.setValueAtTime(fStart, t);
      f.frequency.exponentialRampToValueAtTime(Math.max(fEnd, 20), t + spoolDuration);
      f.Q.value = q;
      const g = ctx.createGain();
      g.gain.setValueAtTime(vol, t);
      g.gain.linearRampToValueAtTime(volEnd, t + spoolDuration);
      src.connect(f).connect(g).connect(dest);
      src.start(t);
      noiseSources.push(src);
    };

    // === SUB-BASS: Deep V8 rumble ===
    osc('sawtooth', 30, 50, 0.01, 0.035);
    osc('sawtooth', 32, 52, 0.008, 0.03);  // detuned bank

    // === LOW-MID: Exhaust growl + firing pulse ===
    osc('square', 65, 130, 0.003, 0.015);

    // Cross-plane crank pulse with LFO
    const pulseOsc = ctx.createOscillator();
    const pulseGain = ctx.createGain();
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();
    pulseOsc.type = 'sawtooth';
    pulseOsc.frequency.setValueAtTime(50, t);
    pulseOsc.frequency.exponentialRampToValueAtTime(100, t + spoolDuration);
    pulseGain.gain.setValueAtTime(0.006, t);
    lfo.type = 'square';
    lfo.frequency.setValueAtTime(2, t);
    lfo.frequency.linearRampToValueAtTime(10, t + spoolDuration);
    lfoGain.gain.setValueAtTime(0.004, t);
    lfoGain.gain.linearRampToValueAtTime(0.012, t + spoolDuration);
    lfo.connect(lfoGain).connect(pulseGain.gain);
    pulseOsc.connect(pulseGain).connect(dest);
    pulseOsc.start(t);
    lfo.start(t);
    engineNodes.push(pulseOsc, lfo);

    // === MID-RANGE: Turbo compressor whine ===
    noise('bandpass', 400, 2200, 1.8, 0.001, 0.014);

    // === HIGH-FREQ: Air rush + whistle + exhaust ===
    noise('bandpass', 2000, 5000, 0.5, 0.0004, 0.004);
    noise('bandpass', 2500, 4500, 4.0, 0.0002, 0.003);
    noise('lowpass', 150, 400, 0.5, 0.004, 0.018);
  },

  /** Cinematic crossfade: engine → layered transition → system idle → silence */
  fadeOutBootHum() {
    if (fadeStarted) return;
    fadeStarted = true;

    const ctx = ensureContext();
    if (!ctx) return;

    const t = ctx.currentTime + 0.02; // tiny offset avoids race with audio thread

    // ============================================================
    // PHASE 1: Engine wind-down (0s → 4s)
    // Fade the single engineMaster gain — controls ALL engine layers
    // setTargetAtTime is glitch-free, approaches 0 from current value
    // tau=1.2 → ~95% gone by 3.6s
    // ============================================================

    if (engineMaster) {
      engineMaster.gain.setTargetAtTime(0, t, 1.2);
    }

    // ============================================================
    // PHASE 2: Transition bridge (0.5s → 5s)
    // New layers that exist ONLY during the crossfade
    // Bridges the gap between engine and idle
    // ============================================================

    const bridgeBuf = createNoiseBuffer(ctx, 8);

    // Low filtered noise — gentle power-down wash (no tonal sweep)
    const washSrc = ctx.createBufferSource();
    washSrc.buffer = bridgeBuf;
    const washFilter = ctx.createBiquadFilter();
    washFilter.type = 'lowpass';
    washFilter.frequency.setValueAtTime(300, t);
    washFilter.frequency.exponentialRampToValueAtTime(80, t + 5.0);
    washFilter.Q.value = 0.4;
    const washGain = ctx.createGain();
    washGain.gain.setValueAtTime(0.0001, t);
    washGain.gain.linearRampToValueAtTime(0.008, t + 1.0);
    washGain.gain.exponentialRampToValueAtTime(0.0001, t + 5.0);
    washSrc.connect(washFilter).connect(washGain).connect(ctx.destination);
    washSrc.start(t);

    // ============================================================
    // PHASE 3: System idle (2s → 12s)
    // Rises slowly underneath the transition, holds, then fades
    // ============================================================

    const idleDuration = 12;

    // Core reactor hum — 55Hz sine
    const idleOsc1 = ctx.createOscillator();
    const idleGain1 = ctx.createGain();
    idleOsc1.type = 'sine';
    idleOsc1.frequency.value = 55;
    idleGain1.gain.setValueAtTime(0.001, t);
    idleGain1.gain.linearRampToValueAtTime(0.008, t + 2.0);  // barely audible at first
    idleGain1.gain.linearRampToValueAtTime(0.03, t + 4.5);   // rises as engine fades
    idleGain1.gain.setValueAtTime(0.03, t + 6.0);             // full hold
    idleGain1.gain.exponentialRampToValueAtTime(0.0001, t + idleDuration);
    idleOsc1.connect(idleGain1).connect(ctx.destination);
    idleOsc1.start(t);

    // Second harmonic — warmth
    const idleOsc2 = ctx.createOscillator();
    const idleGain2 = ctx.createGain();
    idleOsc2.type = 'sine';
    idleOsc2.frequency.value = 110;
    idleGain2.gain.setValueAtTime(0.001, t);
    idleGain2.gain.linearRampToValueAtTime(0.004, t + 2.0);
    idleGain2.gain.linearRampToValueAtTime(0.014, t + 4.5);
    idleGain2.gain.setValueAtTime(0.014, t + 6.0);
    idleGain2.gain.exponentialRampToValueAtTime(0.0001, t + idleDuration);
    idleOsc2.connect(idleGain2).connect(ctx.destination);
    idleOsc2.start(t);

    // Third harmonic — slight presence
    const idleOsc3 = ctx.createOscillator();
    const idleGain3 = ctx.createGain();
    idleOsc3.type = 'sine';
    idleOsc3.frequency.value = 165;
    idleGain3.gain.setValueAtTime(0.001, t);
    idleGain3.gain.linearRampToValueAtTime(0.002, t + 2.5);
    idleGain3.gain.linearRampToValueAtTime(0.006, t + 5.0);
    idleGain3.gain.setValueAtTime(0.006, t + 6.0);
    idleGain3.gain.exponentialRampToValueAtTime(0.0001, t + idleDuration);
    idleOsc3.connect(idleGain3).connect(ctx.destination);
    idleOsc3.start(t);

    // Very low sub-harmonic — felt more than heard
    const idleOsc4 = ctx.createOscillator();
    const idleGain4 = ctx.createGain();
    idleOsc4.type = 'sine';
    idleOsc4.frequency.value = 27.5;
    idleGain4.gain.setValueAtTime(0.001, t);
    idleGain4.gain.linearRampToValueAtTime(0.015, t + 4.5);
    idleGain4.gain.setValueAtTime(0.015, t + 6.0);
    idleGain4.gain.exponentialRampToValueAtTime(0.0001, t + idleDuration);
    idleOsc4.connect(idleGain4).connect(ctx.destination);
    idleOsc4.start(t);

    // Ventilation noise — low-pass filtered, data center ambience
    const idleNoiseBuf = createNoiseBuffer(ctx, idleDuration + 1);
    const idleNoiseSrc = ctx.createBufferSource();
    idleNoiseSrc.buffer = idleNoiseBuf;
    const idleNoiseFilter = ctx.createBiquadFilter();
    idleNoiseFilter.type = 'lowpass';
    idleNoiseFilter.frequency.value = 250;
    idleNoiseFilter.Q.value = 0.4;
    const idleNoiseGain = ctx.createGain();
    idleNoiseGain.gain.setValueAtTime(0.001, t);
    idleNoiseGain.gain.linearRampToValueAtTime(0.003, t + 2.0);
    idleNoiseGain.gain.linearRampToValueAtTime(0.01, t + 4.5);
    idleNoiseGain.gain.setValueAtTime(0.01, t + 6.0);
    idleNoiseGain.gain.exponentialRampToValueAtTime(0.0001, t + idleDuration);
    idleNoiseSrc.connect(idleNoiseFilter).connect(idleNoiseGain).connect(ctx.destination);
    idleNoiseSrc.start(t);

    // High-frequency data processing texture — very subtle
    const dataNoiseSrc = ctx.createBufferSource();
    dataNoiseSrc.buffer = idleNoiseBuf;
    const dataFilter = ctx.createBiquadFilter();
    dataFilter.type = 'bandpass';
    dataFilter.frequency.value = 2000;
    dataFilter.Q.value = 2.0;
    const dataNoiseGain = ctx.createGain();
    dataNoiseGain.gain.setValueAtTime(0.001, t);
    dataNoiseGain.gain.linearRampToValueAtTime(0.003, t + 4.5);
    dataNoiseGain.gain.setValueAtTime(0.003, t + 6.0);
    dataNoiseGain.gain.exponentialRampToValueAtTime(0.0001, t + idleDuration);
    dataNoiseSrc.connect(dataFilter).connect(dataNoiseGain).connect(ctx.destination);
    dataNoiseSrc.start(t);

    // ============================================================
    // Cleanup
    // ============================================================

    // Stop engine layers after they've faded (tau*5 = fully inaudible)
    setTimeout(() => {
      for (const node of engineNodes) {
        try { node.stop(); } catch { /* */ }
      }
      engineNodes = [];
      for (const ns of noiseSources) {
        try { ns.stop(); } catch { /* */ }
      }
      noiseSources = [];
      if (engineMaster) {
        engineMaster.disconnect();
        engineMaster = null;
      }
    }, 6000);

    // Stop bridge layers
    setTimeout(() => {
      try { washSrc.stop(); } catch { /* */ }
    }, 5500);

    // Stop idle layers
    setTimeout(() => {
      try { idleOsc1.stop(); } catch { /* */ }
      try { idleOsc2.stop(); } catch { /* */ }
      try { idleOsc3.stop(); } catch { /* */ }
      try { idleOsc4.stop(); } catch { /* */ }
      try { idleNoiseSrc.stop(); } catch { /* */ }
      try { dataNoiseSrc.stop(); } catch { /* */ }
    }, idleDuration * 1000 + 200);
  },

  /** Key tick — high holographic ping */
  playKeyTick() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const t = ctx.currentTime;

    // Dual-tone shimmer — two close frequencies create holographic beating
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();
    osc1.type = 'sine';
    osc2.type = 'sine';
    osc1.frequency.value = 6200;
    osc2.frequency.value = 6600;
    gain.gain.setValueAtTime(0.015, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.025);
    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);
    osc1.start(t);
    osc2.start(t);
    osc1.stop(t + 0.025);
    osc2.stop(t + 0.025);
  },

  /** Boot tick — shell appearing ping */
  playBootTick() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const t = ctx.currentTime;

    // Quick crystalline tap
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 5800;
    gain.gain.setValueAtTime(0.02, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.02);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t);
    osc.stop(t + 0.02);

    // Shimmer overtone
    const echo = ctx.createOscillator();
    const echoGain = ctx.createGain();
    echo.type = 'sine';
    echo.frequency.value = 8400;
    echoGain.gain.setValueAtTime(0.006, t);
    echoGain.gain.exponentialRampToValueAtTime(0.001, t + 0.015);
    echo.connect(echoGain).connect(ctx.destination);
    echo.start(t);
    echo.stop(t + 0.015);
  },

  /** Check confirm — double holographic chime */
  playCheckConfirm() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const t = ctx.currentTime;

    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = 'sine';
    osc1.frequency.value = 6400;
    gain1.gain.setValueAtTime(0.02, t);
    gain1.gain.exponentialRampToValueAtTime(0.001, t + 0.015);
    osc1.connect(gain1).connect(ctx.destination);
    osc1.start(t);
    osc1.stop(t + 0.015);

    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = 'sine';
    osc2.frequency.value = 7200;
    gain2.gain.setValueAtTime(0.012, t + 0.015);
    gain2.gain.exponentialRampToValueAtTime(0.001, t + 0.03);
    osc2.connect(gain2).connect(ctx.destination);
    osc2.start(t + 0.015);
    osc2.stop(t + 0.03);
  },

  /** Widget online — holographic activation ping */
  playWidgetOnline() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const t = ctx.currentTime;

    // Primary crystalline ping
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 6800;
    gain.gain.setValueAtTime(0.022, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.03);
    osc.connect(gain).connect(ctx.destination);
    osc.start(t);
    osc.stop(t + 0.03);

    // Soft harmonic tail
    const echo = ctx.createOscillator();
    const echoGain = ctx.createGain();
    echo.type = 'sine';
    echo.frequency.value = 9200;
    echoGain.gain.setValueAtTime(0.005, t + 0.01);
    echoGain.gain.exponentialRampToValueAtTime(0.001, t + 0.04);
    echo.connect(echoGain).connect(ctx.destination);
    echo.start(t + 0.01);
    echo.stop(t + 0.04);
  },

  /** Boot complete — ascending sweep 600->900Hz */
  playBootComplete() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(600, ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(900, ctx.currentTime + 0.15);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.2);
  },

  /** Startup chord — plays during dissolve phase */
  playStartupChord() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    [440, 554, 660].forEach((freq) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.001, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.05, ctx.currentTime + 0.15);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.6);
    });
  },

  /** Alias for backward compatibility */
  playStartupTone() {
    this.playStartupChord();
  },
};
