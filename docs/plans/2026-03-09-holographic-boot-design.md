# Holographic Boot Sequence & Living UI — Design Doc

**Status:** Approved
**Date:** 2026-03-09

---

## Overview

Replace the current terminal-style boot sequence with a JARVIS-inspired holographic boot that transitions into a subtly alive app UI. The boot is the show (full HUD theatrics); the app at rest stays functional with minimal ambient animation.

## Boot Sequence (5–10 seconds)

### Phase 1: Frame Draw (~1.5s)
- Black screen. A single horizontal line draws itself across the center of the screen (CSS border animation, left-to-right).
- Line splits into a full rectangular frame outline (top/bottom/left/right edges draw outward from center).
- Faint cyan/blue color, 1px stroke.
- **Sound:** Low hum begins (procedural oscillator, ~60Hz base, very low gain).

### Phase 2: Identity (~1.5s)
- "SPECTRE" types itself inside the frame, monospace, letter by letter with blinking cursor.
- Version number (v2.2.0) fades in below the title, smaller font.
- Faint blueprint-style grid lines appear across the full background behind the frame.
- **Sound:** Hum continues building. Soft key tick per letter typed.

### Phase 3: System Checks (~3–4s)
- System check lines appear one by one inside the frame, below the title.
- Each line has bracket markers `[ ]` on the left.
- As backend reports ready (or on timer), brackets fill to `[✓]` with a brief pulse glow on the checkmark.
- Lines: Database, Market Data, Model Engine, Universe Scan, Portfolio Sync, Watchlists, Market Feeds, UI Components.
- **Sound:** Hum rising slowly. Soft tick per line appearance. Subtle confirmation tone per checkmark.

### Phase 4: Frame Dissolve & App Materialization (~2–3s)
- The HUD frame breaks apart — top edge slides up and becomes the ModuleTabBar position, side edges fade, bottom edge fades.
- Grid background fades to the app's normal `--bg-primary`.
- Dashboard widgets materialize individually with staggered timing:
  1. Market Overview (top-left) — fades in with brief blue edge glow
  2. Portfolio Summary (top-right) — 300ms later
  3. Watchlist (middle) — 300ms later
  4. Recent Models (bottom-left) + Upcoming Events (bottom-right) — 300ms later
- Each widget has a "power-on" flash: border briefly glows brighter, then settles to ambient level.
- **Sound:** Hum crescendos to peak as widgets appear, then fades out over ~2s after last widget.

## App at Rest — Living UI

### Panel Glow
- All widget/card panels get a `box-shadow` with a faint blue glow: `0 0 8px rgba(59, 130, 246, 0.06)`.
- On hover, glow increases: `0 0 12px rgba(59, 130, 246, 0.12)`. Transition: 300ms.

### Ambient Pulse
- Panel borders have a CSS animation that oscillates opacity between 0.97 and 1.0 over 4 seconds. Nearly imperceptible but creates a living feel.
- Animation: `@keyframes ambientPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.97; } }` on border color.

### Tab Bar Glow
- Active tab underline gets a soft glow shadow instead of flat color: `0 2px 8px rgba(59, 130, 246, 0.3)`.

### Page Transitions
- Content area transitions use existing cascade system. No changes needed — the widget stagger already works well.

### Data Loading Scan Line
- When a widget is loading data, a thin horizontal line (1px, accent color, low opacity) sweeps top-to-bottom across the widget. CSS animation, ~1.5s duration.
- Replaces or supplements any existing loading spinners.

## Sound Design

All procedural (Web Audio API), no audio files needed.

### Boot Hum
- Base: 60Hz sine wave, starts at gain 0.01.
- Layer: 120Hz sine (octave harmonic) at 0.005 gain.
- Both ramp up linearly over the full boot duration to ~0.08 and ~0.04 respectively.
- After boot complete, exponential ramp down to 0.001 over 2 seconds, then stop.

### Boot Tick (per line/letter)
- 800Hz sine, 30ms duration, gain 0.04. Slightly shorter and quieter than current.

### Check Confirmation
- 1200Hz sine, 80ms, gain 0.05. Quick ascending ping.

### Startup Chord (at widget materialization peak)
- 3-note chord (440, 554, 660 Hz), 600ms, gain ramps up to 0.06 then fades.
- Layered on top of the hum at its crescendo.

## Files to Modify/Create

### Modify
- `frontend/src/components/BootSequence/BootSequence.tsx` — new phase system (4→5 phases, longer timings)
- `frontend/src/components/BootSequence/BootPhase.tsx` — replace terminal layout with HUD frame + system checks
- `frontend/src/components/BootSequence/BootSequence.module.css` — all new animations (line draw, frame, grid, dissolve)
- `frontend/src/services/soundManager.ts` — add hum engine, refine ticks, add check confirmation
- `frontend/src/pages/Dashboard/DashboardPage.tsx` — coordinate widget materialization with boot completion
- `frontend/src/pages/Dashboard/DashboardPage.module.css` — add glow, ambient pulse, scan line animations
- `frontend/src/styles/variables.css` — add glow/holographic CSS variables
- `frontend/src/components/Navigation/ModuleTabBar.tsx` or its CSS — active tab glow

### Create
- None expected. All changes are modifications to existing files.

## What Does NOT Change
- Layout grid, spacing, typography
- Color palette (dark + blue accent) — glow is additive, not replacing
- Data display, readability, content areas
- Existing page routing and component structure
