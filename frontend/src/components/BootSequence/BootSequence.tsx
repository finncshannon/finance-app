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
      const next = nextPhase[phase] as BootPhase | undefined;
      if (!next) return;
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
