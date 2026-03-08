# Session 7B — Sound Infrastructure
## Phase 7: Dashboard

**Priority:** Low
**Type:** Frontend + Minor Backend
**Depends On:** None (can be built independently of 7A, but logically follows it)
**Spec Reference:** `specs/phase7_dashboard.md` → Area 1C

---

## SCOPE SUMMARY

Build the plumbing for startup sounds using the Web Audio API. Create a `soundManager` service with methods for boot tick, boot complete, and startup tone sounds. Hook these into the boot sequence. Add a sound toggle in Settings → General. Ship with procedural oscillator-based placeholder sounds (real audio files will be added later by Finn).

---

## TASKS

### Task 1: Create Sound Manager Service
**Description:** Create a new `soundManager.ts` service that uses the Web Audio API to play procedural sounds, with a settings-driven enable/disable toggle.

**Subtasks:**
- [ ] 1.1 — Create `frontend/src/services/soundManager.ts` with the following API:
  - `initAudioContext()` — lazily create an `AudioContext` (needed due to browser autoplay policies; call on first user interaction or boot start)
  - `playBootTick()` — play a short, high-pitched digital click (~50ms, 800Hz sine wave with fast decay envelope)
  - `playBootComplete()` — play an ascending two-note tone (~200ms, e.g. 600Hz→900Hz sine with smooth envelope)
  - `playStartupTone()` — play a brief ambient chord/swell (~400ms, layered sine waves e.g. 440Hz + 554Hz + 660Hz with gradual attack and release)
  - `isSoundEnabled()` — check `settingsStore` for `sound_enabled` setting
  - All play methods are no-ops when sound is disabled or AudioContext is not initialized
- [ ] 1.2 — Each procedural sound should use `OscillatorNode` + `GainNode` for envelope shaping. Keep the implementation simple and clean.
- [ ] 1.3 — Export a singleton `soundManager` object (not a class instance — just a plain object with methods).

**Implementation Notes:**
- Use `settingsStore.getState().settings.sound_enabled` to check the toggle. If the setting is `'false'` (string, since all settings are stored as strings), skip playback.
- AudioContext must be created after a user gesture (browser policy). The boot sequence technically starts automatically, but the Electron environment may not enforce this restriction. Still, defensively call `initAudioContext()` at the start of the boot sequence.
- Procedural sounds direction: futuristic / holographic feel (Star Wars, Iron Man aesthetic). Boot ticks are short clean digital clicks, completion is an ascending resolve, startup tone is a brief ambient swell.

---

### Task 2: Integrate Sound Hooks into Boot Sequence
**Description:** Call sound manager methods at appropriate points during the boot animation.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/components/BootSequence/BootPhase.tsx`, call `soundManager.playBootTick()` each time a new boot line becomes visible (inside the stagger timer loop, when `setVisibleLines(i + 1)` fires).
- [ ] 2.2 — In `BootPhase.tsx`, call `soundManager.playBootComplete()` when all checkmarks are visible (when the completion line becomes visible, i.e., after the "All systems online" line appears — or if 7A hasn't been built yet, after `visibleChecks === BOOT_LINES.length`).
- [ ] 2.3 — In `frontend/src/components/BootSequence/BootSequence.tsx`, call `soundManager.initAudioContext()` when the component mounts (in a `useEffect` with empty deps). Call `soundManager.playStartupTone()` when `phase` transitions to `'shift'` (the "all systems go" moment).
- [ ] 2.4 — Import `soundManager` from `@/services/soundManager` in both files.

**Implementation Notes:**
- The boot tick should fire for each line appearance. Since lines stagger at ~110ms apart (if 7A is built) or 70ms (if not), the tick sounds will create a rhythmic clicking pattern.
- `playBootComplete()` fires once after all checkmarks, `playStartupTone()` fires once at the shift transition. These should not overlap significantly — there's a natural gap between checkmark completion and the shift phase.

---

### Task 3: Add Sound Toggle in Settings
**Description:** Add a `sound_enabled` setting to the backend defaults and a toggle checkbox in Settings → General.

**Subtasks:**
- [ ] 3.1 — In `backend/services/settings_service.py`, add `"sound_enabled": "true"` to `DEFAULT_SETTINGS` dictionary.
- [ ] 3.2 — In `frontend/src/pages/Settings/sections/GeneralSection.tsx`, add a `Checkbox` component for "Enable startup sounds" below the existing "Enable boot animation" checkbox. It should read/write `sound_enabled` from `settingsStore`.

**Implementation Notes:**
- The existing `GeneralSection.tsx` already has a `Checkbox` for `boot_animation_enabled` — follow the same pattern for `sound_enabled`.
- The `settingsStore` pattern: `settings.sound_enabled` is a string `'true'` or `'false'`. The checkbox should use `checked={settings.sound_enabled === 'true'}` and `onChange={(checked) => setSetting('sound_enabled', checked ? 'true' : 'false')}`.

---

### Task 4: Create Sounds Directory
**Description:** Create the sounds directory for future audio assets.

**Subtasks:**
- [ ] 4.1 — Create empty directory `frontend/public/sounds/` (or ensure it exists). This is where Finn will later add real audio files (`.mp3` or `.wav`) to replace the procedural fallbacks.
- [ ] 4.2 — Optionally, add a `README.md` in the sounds directory explaining the expected file names: `boot-tick.mp3`, `boot-complete.mp3`, `startup-tone.mp3`.

**Implementation Notes:**
- The soundManager currently uses only procedural (oscillator-based) sounds. A future update could check for files in `sounds/` and prefer them over procedural generation. This is out of scope for 7B.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `frontend/src/services/soundManager.ts` exists and exports `initAudioContext()`, `playBootTick()`, `playBootComplete()`, `playStartupTone()`.
- [ ] AC-2: All sound methods are no-ops when `sound_enabled` setting is `'false'`.
- [ ] AC-3: All sound methods are no-ops when AudioContext is not initialized.
- [ ] AC-4: `playBootTick()` produces a short digital click sound (~50ms) using an oscillator.
- [ ] AC-5: `playBootComplete()` produces an ascending tone (~200ms) using an oscillator.
- [ ] AC-6: `playStartupTone()` produces a brief chord/swell (~400ms) using layered oscillators.
- [ ] AC-7: Boot tick plays on each boot line appearance in `BootPhase.tsx`.
- [ ] AC-8: Boot complete plays when all checkmarks finish.
- [ ] AC-9: Startup tone plays when boot transitions to "shift" phase.
- [ ] AC-10: Settings → General has a "Enable startup sounds" checkbox.
- [ ] AC-11: `sound_enabled` defaults to `'true'` in backend `DEFAULT_SETTINGS`.
- [ ] AC-12: Toggling the checkbox off immediately prevents sounds from playing on next boot.
- [ ] AC-13: `frontend/public/sounds/` directory exists.
- [ ] AC-14: No audio errors in console when sounds are disabled.
- [ ] AC-15: AudioContext is initialized lazily (not on module import).

---

## FILES TOUCHED

**New files:**
- `frontend/src/services/soundManager.ts` — Web Audio API sound manager
- `frontend/public/sounds/` — empty directory for future audio assets
- `frontend/public/sounds/README.md` — optional, documents expected file names

**Modified files:**
- `frontend/src/components/BootSequence/BootPhase.tsx` — import soundManager, call `playBootTick()` on line appearance, `playBootComplete()` on checkmarks done
- `frontend/src/components/BootSequence/BootSequence.tsx` — import soundManager, call `initAudioContext()` on mount, `playStartupTone()` on shift phase
- `frontend/src/pages/Settings/sections/GeneralSection.tsx` — add sound_enabled checkbox
- `backend/services/settings_service.py` — add `sound_enabled` to DEFAULT_SETTINGS

---

## BUILDER PROMPT

> **Session 7B — Sound Infrastructure**
>
> You are building session 7B of the Finance App v2.0 update.
>
> **What you're doing:** Building the sound infrastructure for boot sequence audio. Creating a `soundManager` service with Web Audio API procedural sounds, hooking it into the boot animation, and adding a settings toggle.
>
> **Context:** The app has a terminal-style boot sequence (BootSequence.tsx + BootPhase.tsx) that animates through 4 phases: black → terminal (boot lines appear with stagger, then checkmarks) → shift → fadeout. You're adding audio feedback at key moments. No real audio files yet — use oscillator-based procedural sounds as placeholders.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`. (Note: `displayNames.ts` does not exist yet — it will be created in session 8A.)
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Create Sound Manager Service**
>
> Create `frontend/src/services/soundManager.ts`:
>
> ```typescript
> // Sound Manager — procedural Web Audio API sounds for boot sequence
> // All methods are no-ops when sound is disabled or AudioContext unavailable
>
> import { useSettingsStore } from '../stores/settingsStore';
>
> let audioCtx: AudioContext | null = null;
>
> function isSoundEnabled(): boolean {
>   return useSettingsStore.getState().settings.sound_enabled !== 'false';
> }
>
> function ensureContext(): AudioContext | null {
>   if (!audioCtx) return null;
>   if (audioCtx.state === 'suspended') audioCtx.resume();
>   return audioCtx;
> }
>
> export const soundManager = {
>   initAudioContext() {
>     if (!audioCtx) {
>       try { audioCtx = new AudioContext(); } catch { /* unsupported */ }
>     }
>   },
>
>   playBootTick() {
>     if (!isSoundEnabled()) return;
>     const ctx = ensureContext();
>     if (!ctx) return;
>     // Short 800Hz sine click, ~50ms
>     const osc = ctx.createOscillator();
>     const gain = ctx.createGain();
>     osc.type = 'sine';
>     osc.frequency.value = 800;
>     gain.gain.setValueAtTime(0.08, ctx.currentTime);
>     gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.05);
>     osc.connect(gain).connect(ctx.destination);
>     osc.start(ctx.currentTime);
>     osc.stop(ctx.currentTime + 0.05);
>   },
>
>   playBootComplete() {
>     if (!isSoundEnabled()) return;
>     const ctx = ensureContext();
>     if (!ctx) return;
>     // Ascending two-note tone: 600Hz → 900Hz, ~200ms
>     const osc = ctx.createOscillator();
>     const gain = ctx.createGain();
>     osc.type = 'sine';
>     osc.frequency.setValueAtTime(600, ctx.currentTime);
>     osc.frequency.linearRampToValueAtTime(900, ctx.currentTime + 0.15);
>     gain.gain.setValueAtTime(0.1, ctx.currentTime);
>     gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
>     osc.connect(gain).connect(ctx.destination);
>     osc.start(ctx.currentTime);
>     osc.stop(ctx.currentTime + 0.2);
>   },
>
>   playStartupTone() {
>     if (!isSoundEnabled()) return;
>     const ctx = ensureContext();
>     if (!ctx) return;
>     // Layered chord swell: 440Hz + 554Hz + 660Hz, ~400ms
>     [440, 554, 660].forEach((freq) => {
>       const osc = ctx.createOscillator();
>       const gain = ctx.createGain();
>       osc.type = 'sine';
>       osc.frequency.value = freq;
>       gain.gain.setValueAtTime(0.001, ctx.currentTime);
>       gain.gain.linearRampToValueAtTime(0.06, ctx.currentTime + 0.1);
>       gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
>       osc.connect(gain).connect(ctx.destination);
>       osc.start(ctx.currentTime);
>       osc.stop(ctx.currentTime + 0.4);
>     });
>   },
> };
> ```
>
> This is a reference implementation — adjust gain values and timings to taste, but keep the overall structure.
>
> **Task 2: Integrate Sound Hooks into Boot Sequence**
>
> In `frontend/src/components/BootSequence/BootSequence.tsx`:
> - Add `import { soundManager } from '../../services/soundManager';`
> - Add a `useEffect` on mount (empty deps) that calls `soundManager.initAudioContext()`
> - In the `useEffect` that watches for `phase === 'shift'`, add `soundManager.playStartupTone()` at the start
>
> In `frontend/src/components/BootSequence/BootPhase.tsx`:
> - Add `import { soundManager } from '../../services/soundManager';`
> - In the boot line stagger loop (where `setVisibleLines(i + 1)` is called), also call `soundManager.playBootTick()`
> - After checkmarks finish (when the last checkmark becomes visible or the completion line shows), call `soundManager.playBootComplete()`. If session 7A has been built (and there's a completion line), trigger on completion line visibility. If not, trigger when `visibleChecks === BOOT_LINES.length`.
>
> **Task 3: Add Sound Toggle in Settings**
>
> In `backend/services/settings_service.py`:
> - Add `"sound_enabled": "true"` to `DEFAULT_SETTINGS` dict (add it near `boot_animation_enabled`)
>
> In `frontend/src/pages/Settings/sections/GeneralSection.tsx`:
> - Below the existing "Enable boot animation" `Checkbox`, add:
> ```tsx
> <Checkbox
>   label="Enable startup sounds"
>   checked={settings.sound_enabled !== 'false'}
>   onChange={(checked) =>
>     setSetting('sound_enabled', checked ? 'true' : 'false')
>   }
> />
> ```
>
> **Task 4: Create Sounds Directory**
> - Create `frontend/public/sounds/` directory
> - Optionally add a `README.md` with: "Place audio files here: `boot-tick.mp3`, `boot-complete.mp3`, `startup-tone.mp3`. When present, soundManager can be updated to prefer these over procedural generation."
>
> **Acceptance criteria:**
> 1. `soundManager.ts` exists and exports `initAudioContext`, `playBootTick`, `playBootComplete`, `playStartupTone`
> 2. All methods are no-ops when `sound_enabled` is `'false'` or AudioContext unavailable
> 3. Boot tick plays on each boot line appearance
> 4. Boot complete plays after all checkmarks
> 5. Startup tone plays at shift phase transition
> 6. Settings → General has "Enable startup sounds" checkbox
> 7. `sound_enabled` defaults to `'true'` in backend
> 8. No console errors when sounds disabled
> 9. AudioContext initialized lazily (not on import)
>
> **Files to create:**
> - `frontend/src/services/soundManager.ts`
> - `frontend/public/sounds/` (directory)
> - `frontend/public/sounds/README.md` (optional)
>
> **Files to modify:**
> - `frontend/src/components/BootSequence/BootPhase.tsx`
> - `frontend/src/components/BootSequence/BootSequence.tsx`
> - `frontend/src/pages/Settings/sections/GeneralSection.tsx`
> - `backend/services/settings_service.py`
>
> **Technical constraints:**
> - Web Audio API only (no external audio libraries)
> - CSS modules for any UI additions
> - Settings stored as strings in SQLite via `settingsStore`
> - Procedural sounds only — no audio file dependencies for now
> - Keep gain levels low (0.06–0.10 max) to avoid startling users
> - Zustand for all state management
