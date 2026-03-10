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

// Persistent hum oscillators (managed across boot lifecycle)
let humOsc1: OscillatorNode | null = null;
let humOsc2: OscillatorNode | null = null;
let humGain1: GainNode | null = null;
let humGain2: GainNode | null = null;

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

  /** Start the low-frequency boot hum — ramps up over boot duration */
  startBootHum() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    // Base hum: 60Hz sine
    humOsc1 = ctx.createOscillator();
    humGain1 = ctx.createGain();
    humOsc1.type = 'sine';
    humOsc1.frequency.value = 60;
    humGain1.gain.setValueAtTime(0.008, ctx.currentTime);
    humGain1.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 8);
    humOsc1.connect(humGain1).connect(ctx.destination);
    humOsc1.start(ctx.currentTime);

    // Harmonic layer: 120Hz sine
    humOsc2 = ctx.createOscillator();
    humGain2 = ctx.createGain();
    humOsc2.type = 'sine';
    humOsc2.frequency.value = 120;
    humGain2.gain.setValueAtTime(0.004, ctx.currentTime);
    humGain2.gain.linearRampToValueAtTime(0.03, ctx.currentTime + 8);
    humOsc2.connect(humGain2).connect(ctx.destination);
    humOsc2.start(ctx.currentTime);
  },

  /** Fade out the boot hum over ~2.5 seconds */
  fadeOutBootHum() {
    const ctx = ensureContext();
    if (!ctx) return;

    const fadeTime = 2.5;
    if (humGain1) {
      humGain1.gain.cancelScheduledValues(ctx.currentTime);
      humGain1.gain.setValueAtTime(humGain1.gain.value, ctx.currentTime);
      humGain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + fadeTime);
    }
    if (humGain2) {
      humGain2.gain.cancelScheduledValues(ctx.currentTime);
      humGain2.gain.setValueAtTime(humGain2.gain.value, ctx.currentTime);
      humGain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + fadeTime);
    }

    setTimeout(() => {
      try { humOsc1?.stop(); } catch { /* already stopped */ }
      try { humOsc2?.stop(); } catch { /* already stopped */ }
      humOsc1 = null;
      humOsc2 = null;
      humGain1 = null;
      humGain2 = null;
    }, fadeTime * 1000 + 100);
  },

  /** Soft key tick for title typing — 1000Hz, 20ms */
  playKeyTick() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 1000;
    gain.gain.setValueAtTime(0.03, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.02);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.02);
  },

  /** Boot tick per system check line — 800Hz, 40ms */
  playBootTick() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 800;
    gain.gain.setValueAtTime(0.04, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.04);
  },

  /** Check confirmation ping — 1200Hz, 60ms */
  playCheckConfirm() {
    if (!isSoundEnabled()) return;
    const ctx = ensureContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = 1200;
    gain.gain.setValueAtTime(0.04, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.06);
    osc.connect(gain).connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.06);
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
