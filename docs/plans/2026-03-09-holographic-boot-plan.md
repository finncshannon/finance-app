# Holographic Boot Sequence & Living UI — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the terminal-style boot with a JARVIS-inspired holographic HUD boot sequence, add ambient "alive" effects to the app UI, and implement a procedural hum-to-crescendo sound engine.

**Architecture:** The boot sequence remains a single overlay component with phased transitions, but the phase count increases from 4 to 5 (frame-draw, identity, system-checks, dissolve, done). The sound manager gains a persistent hum oscillator that runs the full boot duration. Living UI effects are applied via CSS variables and keyframes added to `variables.css` and the dashboard/widget/tab-bar stylesheets.

**Tech Stack:** React 18, CSS Modules, CSS keyframes/animations, Web Audio API (procedural synthesis), Zustand state store.

---

### Task 1: Add Holographic CSS Variables

**Files:**
- Modify: `frontend/src/styles/variables.css:1-70`

**Step 1: Add glow and holographic tokens to variables.css**

Add these after the existing `--transition-page` line (line 69):

```css
  /* Holographic / Glow */
  --glow-color: rgba(59, 130, 246, 0.08);
  --glow-color-hover: rgba(59, 130, 246, 0.15);
  --glow-color-strong: rgba(59, 130, 246, 0.25);
  --glow-color-boot: rgba(59, 130, 246, 0.4);
  --hud-cyan: #3B82F6;
  --hud-cyan-dim: rgba(59, 130, 246, 0.3);
  --hud-grid-color: rgba(59, 130, 246, 0.04);
  --transition-boot: 400ms ease;
```

**Step 2: Verify the app still compiles**

Run: `cd "G:/Claude Access Point/StockValuation/Finance App/frontend" && npx tsc --noEmit`
Expected: No errors.

**Step 3: Commit**

```bash
git add frontend/src/styles/variables.css
git commit -m "feat(ui): add holographic glow CSS variables"
```

---

### Task 2: Rewrite BootSequence Component — Phase Engine

**Files:**
- Modify: `frontend/src/components/BootSequence/BootSequence.tsx` (full rewrite)

**Step 1: Replace BootSequence.tsx with new 5-phase engine**

The new phases are: `black` (300ms) → `frame` (1500ms) → `identity` (1800ms) → `checks` (3500ms) → `dissolve` (2000ms) → `done`.

```tsx
import { useState, useEffect, useRef, useCallback } from 'react';
import styles from './BootSequence.module.css';
import { BootHUD } from './BootHUD';
import { soundManager } from '../../services/soundManager';

interface BootSequenceProps {
  backendReady: boolean;
  onBootComplete: () => void;
}

export type BootPhase = 'black' | 'frame' | 'identity' | 'checks' | 'dissolve' | 'done';

const PHASE_TIMINGS: Record<Exclude<BootPhase, 'done'>, number> = {
  black: 300,
  frame: 1500,
  identity: 1800,
  checks: 3500,
  dissolve: 2000,
};

export function BootSequence({ backendReady, onBootComplete }: BootSequenceProps) {
  const [phase, setPhase] = useState<BootPhase>('black');
  const bootStart = useRef(performance.now());
  const completeCalled = useRef(false);

  useEffect(() => {
    soundManager.initAudioContext();
  }, []);

  // Start hum when frame phase begins
  useEffect(() => {
    if (phase === 'frame') {
      soundManager.startBootHum();
    }
  }, [phase]);

  // Phase progression
  useEffect(() => {
    if (phase === 'done') return;

    const nextPhase: Record<string, BootPhase> = {
      black: 'frame',
      frame: 'identity',
      identity: 'checks',
      checks: 'dissolve',
      dissolve: 'done',
    };

    // For checks phase, wait for backend ready before advancing
    if (phase === 'checks' && !backendReady) return;

    const duration = PHASE_TIMINGS[phase as Exclude<BootPhase, 'done'>];
    const timer = setTimeout(() => {
      const next = nextPhase[phase];
      if (next === 'dissolve') {
        soundManager.fadeOutBootHum();
        soundManager.playStartupChord();
      }
      setPhase(next);
    }, duration);

    return () => clearTimeout(timer);
  }, [phase, backendReady]);

  const handleComplete = useCallback(() => {
    if (completeCalled.current) return;
    completeCalled.current = true;
    const elapsed = Math.round(performance.now() - bootStart.current);
    console.log(`[boot] Complete in ${elapsed}ms`);
    onBootComplete();
  }, [onBootComplete]);

  useEffect(() => {
    if (phase === 'done') handleComplete();
  }, [phase, handleComplete]);

  if (phase === 'done') return null;

  return (
    <div className={`${styles.overlay} ${phase === 'dissolve' ? styles.overlayDissolve : ''}`}>
      <BootHUD phase={phase} backendReady={backendReady} />
    </div>
  );
}
```

**Step 2: Verify TypeScript compiles (will fail until BootHUD exists — expected)**

Run: `npx tsc --noEmit 2>&1 | head -5`
Expected: Error about missing `./BootHUD` module. This is resolved in Task 3.

---

### Task 3: Create BootHUD Component (replaces BootPhase)

**Files:**
- Create: `frontend/src/components/BootSequence/BootHUD.tsx`
- Delete content of: `frontend/src/components/BootSequence/BootPhase.tsx` (keep file, re-export BootHUD for safety)

**Step 1: Create BootHUD.tsx**

This component renders the HUD frame, title, grid, and system check lines. Each element is visibility-gated by the current phase.

```tsx
import { useState, useEffect } from 'react';
import styles from './BootSequence.module.css';
import { soundManager } from '../../services/soundManager';
import type { BootPhase } from './BootSequence';

interface BootHUDProps {
  phase: BootPhase;
  backendReady: boolean;
}

const SYSTEM_CHECKS = [
  'Database connected',
  'Market data service',
  'Model engine loaded',
  'Scanning universe',
  'Syncing portfolio',
  'Loading watchlists',
  'Connecting market feeds',
  'UI components ready',
];

const CHECK_STAGGER_MS = 350;
const CHECK_CONFIRM_MS = 120;

export function BootHUD({ phase, backendReady }: BootHUDProps) {
  const [titleChars, setTitleChars] = useState(0);
  const [showVersion, setShowVersion] = useState(false);
  const [visibleChecks, setVisibleChecks] = useState(0);
  const [confirmedChecks, setConfirmedChecks] = useState(0);
  const [allConfirmed, setAllConfirmed] = useState(false);

  const title = 'SPECTRE';

  // Type out title letter by letter during identity phase
  useEffect(() => {
    if (phase !== 'identity' && phase !== 'checks' && phase !== 'dissolve') {
      return;
    }
    if (titleChars >= title.length) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = titleChars; i < title.length; i++) {
      timers.push(
        setTimeout(() => {
          setTitleChars(i + 1);
          soundManager.playKeyTick();
        }, (i - titleChars) * 100)
      );
    }
    // Show version after title completes
    timers.push(
      setTimeout(() => {
        setShowVersion(true);
      }, title.length * 100 + 300)
    );

    return () => timers.forEach(clearTimeout);
  }, [phase, titleChars]);

  // Stagger system check lines during checks phase
  useEffect(() => {
    if (phase !== 'checks') return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 0; i < SYSTEM_CHECKS.length; i++) {
      timers.push(
        setTimeout(() => {
          setVisibleChecks(i + 1);
          soundManager.playBootTick();
        }, i * CHECK_STAGGER_MS)
      );
    }
    return () => timers.forEach(clearTimeout);
  }, [phase]);

  // Confirm checkmarks once backend is ready and all lines visible
  useEffect(() => {
    if (!backendReady || visibleChecks < SYSTEM_CHECKS.length) return;
    if (allConfirmed) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 0; i < SYSTEM_CHECKS.length; i++) {
      timers.push(
        setTimeout(() => {
          setConfirmedChecks(i + 1);
          soundManager.playCheckConfirm();
        }, i * CHECK_CONFIRM_MS)
      );
    }
    timers.push(
      setTimeout(() => {
        setAllConfirmed(true);
      }, SYSTEM_CHECKS.length * CHECK_CONFIRM_MS + 100)
    );

    return () => timers.forEach(clearTimeout);
  }, [backendReady, visibleChecks, allConfirmed]);

  const showFrame = phase !== 'black';
  const showGrid = phase === 'identity' || phase === 'checks' || phase === 'dissolve';
  const showTitle = phase === 'identity' || phase === 'checks' || phase === 'dissolve';
  const showChecks = phase === 'checks' || phase === 'dissolve';

  return (
    <>
      {/* Background grid */}
      {showGrid && <div className={styles.hudGrid} />}

      {/* HUD Frame */}
      <div className={`${styles.hudFrame} ${showFrame ? styles.hudFrameVisible : ''} ${phase === 'dissolve' ? styles.hudFrameDissolve : ''}`}>
        {/* Title area */}
        {showTitle && (
          <div className={styles.hudTitleArea}>
            <div className={styles.hudTitle}>
              {title.slice(0, titleChars)}
              {titleChars < title.length && <span className={styles.hudCursor}>|</span>}
            </div>
            <div className={`${styles.hudVersion} ${showVersion ? styles.hudVersionVisible : ''}`}>
              v2.2.0
            </div>
          </div>
        )}

        {/* System checks */}
        {showChecks && (
          <div className={styles.hudChecks}>
            {SYSTEM_CHECKS.map((label, i) => (
              <div
                key={i}
                className={`${styles.hudCheckLine} ${i < visibleChecks ? styles.hudCheckLineVisible : ''}`}
              >
                <span className={styles.hudBracket}>
                  {i < confirmedChecks ? (
                    <span className={styles.hudCheckmark}>&#10003;</span>
                  ) : (
                    <span className={styles.hudCheckEmpty}>&nbsp;</span>
                  )}
                </span>
                <span className={styles.hudCheckLabel}>{label}</span>
              </div>
            ))}
            {allConfirmed && (
              <div className={`${styles.hudStatusComplete} ${styles.hudCheckLineVisible}`}>
                All systems online
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
```

**Step 2: Update BootPhase.tsx to re-export (backward compat)**

Replace contents of `BootPhase.tsx` with:

```tsx
// Legacy — BootHUD replaces BootPhase
export { BootHUD as BootPhase } from './BootHUD';
```

**Step 3: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors (soundManager new methods will be added in Task 5).

---

### Task 4: Rewrite BootSequence CSS — HUD Animations

**Files:**
- Modify: `frontend/src/components/BootSequence/BootSequence.module.css` (full rewrite)

**Step 1: Replace with holographic HUD styles**

```css
/* BootSequence — Holographic HUD Boot */

/* ── Overlay ── */
.overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: var(--bg-primary, #0D0D0D);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.overlayDissolve {
  opacity: 0;
  transition: opacity 1.8s ease-out;
}

/* ── Background Grid ── */
.hudGrid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(var(--hud-grid-color, rgba(59,130,246,0.04)) 1px, transparent 1px),
    linear-gradient(90deg, var(--hud-grid-color, rgba(59,130,246,0.04)) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0;
  animation: gridFadeIn 1.5s ease-out forwards;
}

@keyframes gridFadeIn {
  to { opacity: 1; }
}

/* ── HUD Frame ── */
.hudFrame {
  position: relative;
  width: 480px;
  max-width: 85vw;
  padding: 40px 48px;
  border: 1px solid transparent;
  opacity: 0;
}

.hudFrameVisible {
  opacity: 1;
  border-color: var(--hud-cyan-dim, rgba(59,130,246,0.3));
  animation: frameDraw 1.2s ease-out forwards;
}

@keyframes frameDraw {
  0% {
    clip-path: inset(50% 50% 50% 50%);
    opacity: 0;
  }
  30% {
    clip-path: inset(49.5% 0% 49.5% 0%);
    opacity: 1;
  }
  100% {
    clip-path: inset(0% 0% 0% 0%);
    opacity: 1;
  }
}

.hudFrameDissolve {
  opacity: 0;
  transform: scale(1.05);
  transition: opacity 1.5s ease-out, transform 1.5s ease-out;
  border-color: transparent;
}

/* Corner brackets */
.hudFrame::before,
.hudFrame::after {
  content: '';
  position: absolute;
  width: 16px;
  height: 16px;
  border-color: var(--hud-cyan, #3B82F6);
  border-style: solid;
  opacity: 0.6;
}

.hudFrame::before {
  top: -1px;
  left: -1px;
  border-width: 2px 0 0 2px;
}

.hudFrame::after {
  top: -1px;
  right: -1px;
  border-width: 2px 2px 0 0;
}

.hudFrameVisible::before,
.hudFrameVisible::after {
  animation: cornerFlash 0.6s ease-out 1s forwards;
}

@keyframes cornerFlash {
  0% { opacity: 0; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}

/* ── Title Area ── */
.hudTitleArea {
  text-align: center;
  margin-bottom: 32px;
}

.hudTitle {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 8px;
  color: var(--hud-cyan, #3B82F6);
  text-shadow: 0 0 20px var(--glow-color-boot, rgba(59,130,246,0.4)),
               0 0 40px rgba(59,130,246,0.15);
}

.hudCursor {
  animation: cursorBlink 0.8s step-end infinite;
  color: var(--hud-cyan, #3B82F6);
}

@keyframes cursorBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.hudVersion {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 11px;
  color: var(--text-tertiary, #737373);
  letter-spacing: 2px;
  margin-top: 8px;
  opacity: 0;
  transform: translateY(4px);
}

.hudVersionVisible {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 400ms ease-out, transform 400ms ease-out;
}

/* ── System Checks ── */
.hudChecks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hudCheckLine {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 12px;
  color: var(--text-tertiary, #737373);
  opacity: 0;
  transform: translateX(-8px);
}

.hudCheckLineVisible {
  opacity: 1;
  transform: translateX(0);
  transition: opacity 250ms ease-out, transform 250ms ease-out;
}

.hudBracket {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: 1px solid var(--hud-cyan-dim, rgba(59,130,246,0.3));
  border-radius: 2px;
  font-size: 11px;
  flex-shrink: 0;
}

.hudCheckEmpty {
  display: inline-block;
  width: 10px;
}

.hudCheckmark {
  color: var(--color-positive, #22C55E);
  text-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
  animation: checkPulse 0.3s ease-out;
}

@keyframes checkPulse {
  0% { transform: scale(0.5); opacity: 0; }
  60% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}

.hudCheckLabel {
  flex: 1;
}

.hudStatusComplete {
  font-family: var(--font-mono, 'JetBrains Mono', monospace);
  font-size: 12px;
  font-weight: 600;
  color: var(--hud-cyan, #3B82F6);
  text-shadow: 0 0 8px var(--glow-color-strong, rgba(59,130,246,0.25));
  margin-top: 8px;
  opacity: 0;
  transform: translateY(4px);
}
```

**Step 2: Verify app compiles**

Run: `npx tsc --noEmit`
Expected: Pass.

**Step 3: Commit**

```bash
git add frontend/src/components/BootSequence/
git commit -m "feat(boot): holographic HUD boot sequence with frame draw and system checks"
```

---

### Task 5: Rewrite Sound Manager — Hum Engine + New Sounds

**Files:**
- Modify: `frontend/src/services/soundManager.ts` (full rewrite)

**Step 1: Replace soundManager.ts**

```typescript
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
let humStartTime = 0;

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

    humStartTime = ctx.currentTime;

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

  /** Fade out the boot hum over ~2 seconds */
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
```

**Step 2: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: Pass.

**Step 3: Commit**

```bash
git add frontend/src/services/soundManager.ts
git commit -m "feat(sound): procedural hum engine with crescendo and holographic sound effects"
```

---

### Task 6: Living UI — Widget Glow, Ambient Pulse, Scan Line

**Files:**
- Modify: `frontend/src/pages/Dashboard/DashboardPage.module.css:82-134`

**Step 1: Update widget base styles with glow and ambient pulse**

Replace the `.widget` block (lines 82-88) and the widget animation blocks (lines 123-134) with:

```css
/* ── Widget Base ── */
.widget {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: 0 0 8px var(--glow-color, rgba(59,130,246,0.08));
  transition: box-shadow var(--transition-panel);
  animation: ambientPulse 4s ease-in-out infinite;
}

.widget:hover {
  box-shadow: 0 0 14px var(--glow-color-hover, rgba(59,130,246,0.15));
}

@keyframes ambientPulse {
  0%, 100% { border-color: var(--border-subtle); }
  50% { border-color: rgba(38, 38, 38, 0.85); }
}
```

**Step 2: Add scan line loading animation**

Add after the `.errorBanner` block:

```css
/* ── Data loading scan line ── */
.widgetLoading {
  position: relative;
  overflow: hidden;
}

.widgetLoading::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    var(--accent-primary) 50%,
    transparent 100%
  );
  opacity: 0.4;
  animation: scanLine 1.5s ease-in-out infinite;
}

@keyframes scanLine {
  0% { top: 0; }
  100% { top: 100%; }
}
```

**Step 3: Update widget entry animation for glow flash**

Replace the existing `.widgetHidden` / `.widgetVisible` (lines 123-134):

```css
/* ── Widget entry animations ── */

.widgetHidden {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
  box-shadow: none;
}

.widgetVisible {
  opacity: 1;
  transform: translateY(0) scale(1);
  transition: opacity 400ms ease-out, transform 400ms ease-out, box-shadow 400ms ease-out;
  animation: widgetPowerOn 0.8s ease-out;
}

@keyframes widgetPowerOn {
  0% {
    box-shadow: 0 0 0px var(--glow-color, rgba(59,130,246,0.08));
  }
  40% {
    box-shadow: 0 0 20px var(--glow-color-strong, rgba(59,130,246,0.25));
  }
  100% {
    box-shadow: 0 0 8px var(--glow-color, rgba(59,130,246,0.08));
  }
}
```

**Step 4: Commit**

```bash
git add frontend/src/pages/Dashboard/DashboardPage.module.css
git commit -m "feat(ui): living dashboard with widget glow, ambient pulse, and scan line loading"
```

---

### Task 7: Living UI — Tab Bar Glow

**Files:**
- Modify: `frontend/src/components/Navigation/ModuleTabBar.module.css`

**Step 1: Update active tab underline to include glow**

Find the `.tab.active::after` rule and replace it:

```css
.tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent-primary);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3),
              0 0px 4px rgba(59, 130, 246, 0.2);
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/Navigation/ModuleTabBar.module.css
git commit -m "feat(ui): active tab glow underline"
```

---

### Task 8: Integration — Wire Boot to Dashboard Cascade

**Files:**
- Modify: `frontend/src/pages/Dashboard/DashboardPage.tsx:12-14`

**Step 1: Increase cascade interval for more dramatic stagger**

Change the constants at lines 12-13:

```typescript
const WIDGET_COUNT = 5;
const CASCADE_INTERVAL_MS = 300;  // was 175 — slower for holographic feel
```

**Step 2: Verify app compiles and commit**

Run: `npx tsc --noEmit`
Expected: Pass.

```bash
git add frontend/src/pages/Dashboard/DashboardPage.tsx
git commit -m "feat(ui): slower widget cascade timing for holographic boot feel"
```

---

### Task 9: Manual QA and Polish

**Step 1: Start the app**

Run: `cd "G:/Claude Access Point/StockValuation/Finance App/electron" && npm run dev`

**Step 2: Visual QA checklist**

- [ ] Boot starts with black screen, then HUD frame draws from center
- [ ] "SPECTRE" types letter by letter with cursor
- [ ] Version fades in below title
- [ ] Blueprint grid visible in background
- [ ] System check lines appear one by one with brackets
- [ ] Checkmarks pulse green once backend responds
- [ ] "All systems online" appears after all checks
- [ ] Frame dissolves, overlay fades out
- [ ] Dashboard widgets cascade in with blue glow flash
- [ ] Widgets have faint ambient glow at rest
- [ ] Hovering a widget brightens the glow
- [ ] Active tab has glow underline
- [ ] Total boot time feels like 5-10 seconds

**Step 3: Audio QA checklist**

- [ ] Low hum starts when frame appears
- [ ] Hum builds gradually throughout boot
- [ ] Soft ticks on title letters and check lines
- [ ] Quick ping on each checkmark confirmation
- [ ] Startup chord plays during dissolve
- [ ] Hum fades out smoothly after dashboard appears
- [ ] No audio pops or clicks

**Step 4: Fix any issues found during QA**

Adjust timings, gains, opacities as needed. CSS-only changes are low risk.

**Step 5: Final commit**

```bash
git add -A
git commit -m "polish: holographic boot timing and visual adjustments"
```

---

### Task 10: Update Log

**Files:**
- Modify: `UPDATE_LOG_v2.2.0.md`

**Step 1: Add entry #18**

```markdown
### 18. Holographic boot sequence and living UI
**Files:** `frontend/src/components/BootSequence/BootSequence.tsx`, `frontend/src/components/BootSequence/BootHUD.tsx`, `frontend/src/components/BootSequence/BootSequence.module.css`, `frontend/src/services/soundManager.ts`, `frontend/src/pages/Dashboard/DashboardPage.module.css`, `frontend/src/components/Navigation/ModuleTabBar.module.css`, `frontend/src/styles/variables.css`
**Type:** enhancement
**Description:** Replaced terminal-style boot with JARVIS-inspired holographic HUD sequence: animated frame draw from center, "SPECTRE" typewriter title, blueprint grid background, bracketed system checks with pulse-glow confirmations, and frame dissolve into app. Sound engine rebuilt with persistent low-frequency hum (60Hz + 120Hz harmonic) that crescendos through boot and fades after dashboard loads. App UI made "alive" with ambient widget glow, hover glow intensification, active tab glow underline, widget power-on flash during cascade, and scan-line loading animation.
```

**Step 2: Commit**

```bash
git add UPDATE_LOG_v2.2.0.md
git commit -m "docs: log holographic boot sequence and living UI (v2.2.0 #18)"
```
