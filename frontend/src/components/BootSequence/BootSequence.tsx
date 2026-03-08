import { useState, useEffect, useRef, useCallback } from 'react';
import styles from './BootSequence.module.css';
import { BootPhase } from './BootPhase';
import { soundManager } from '../../services/soundManager';

interface BootSequenceProps {
  /** true when FastAPI health check passes */
  backendReady: boolean;
  /** Called when animation finishes; app should become interactive */
  onBootComplete: () => void;
}

type Phase = 'black' | 'terminal' | 'shift' | 'fadeout' | 'done';

// Phase timing (ms)
const PHASE_BLACK_DURATION = 300;
const PHASE_TERMINAL_DURATION = 1500;
const PHASE_SHIFT_DURATION = 800;
const PHASE_FADEOUT_DURATION = 600;

export function BootSequence({ backendReady, onBootComplete }: BootSequenceProps) {
  const [phase, setPhase] = useState<Phase>('black');
  const bootStart = useRef(performance.now());
  const completeCalled = useRef(false);

  // Initialize audio context on mount
  useEffect(() => {
    soundManager.initAudioContext();
  }, []);

  // Phase 1 -> Phase 2
  useEffect(() => {
    const timer = setTimeout(() => {
      setPhase('terminal');
    }, PHASE_BLACK_DURATION);

    return () => clearTimeout(timer);
  }, []);

  // Phase 2 -> Phase 3
  useEffect(() => {
    if (phase !== 'terminal') return;

    const timer = setTimeout(() => {
      setPhase('shift');
    }, PHASE_TERMINAL_DURATION);

    return () => clearTimeout(timer);
  }, [phase]);

  // Phase 3 -> Phase 4
  useEffect(() => {
    if (phase !== 'shift') return;

    soundManager.playStartupTone();

    const timer = setTimeout(() => {
      setPhase('fadeout');
    }, PHASE_SHIFT_DURATION);

    return () => clearTimeout(timer);
  }, [phase]);

  // Phase 4 -> done (after CSS transition completes)
  useEffect(() => {
    if (phase !== 'fadeout') return;

    const timer = setTimeout(() => {
      setPhase('done');
    }, PHASE_FADEOUT_DURATION);

    return () => clearTimeout(timer);
  }, [phase]);

  // Fire completion callback
  const handleComplete = useCallback(() => {
    if (completeCalled.current) return;
    completeCalled.current = true;

    const elapsed = Math.round(performance.now() - bootStart.current);
    console.log(`[boot] Complete in ${elapsed}ms`);
    onBootComplete();
  }, [onBootComplete]);

  useEffect(() => {
    if (phase === 'done') {
      handleComplete();
    }
  }, [phase, handleComplete]);

  // Don't render anything once fully done
  if (phase === 'done') return null;

  const overlayPhaseClass =
    phase === 'black' ? styles.phaseBlack :
    phase === 'terminal' ? styles.phaseTerminal :
    phase === 'shift' ? styles.phaseShift :
    styles.phaseFadeOut;

  const terminalShifted = phase === 'shift' || phase === 'fadeout';

  return (
    <div className={`${styles.overlay} ${overlayPhaseClass}`}>
      <div
        className={`${styles.terminal} ${terminalShifted ? styles.terminalShifted : ''}`}
      >
        <BootPhase
          active={phase !== 'black'}
          backendReady={backendReady}
        />
      </div>
    </div>
  );
}
