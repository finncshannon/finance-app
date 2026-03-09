import { useState, useEffect } from 'react';
import styles from './BootSequence.module.css';
import { soundManager } from '../../services/soundManager';

interface BootLineConfig {
  prefix: string;
  label: string;
}

interface BootPhaseProps {
  /** Whether this phase is active and lines should start appearing */
  active: boolean;
  /** Whether the backend is ready (drives checkmark animation) */
  backendReady: boolean;
  /** Stagger delay between each line in ms */
  staggerMs?: number;
}

const BOOT_LINES: BootLineConfig[] = [
  { prefix: '├──', label: 'Database connected' },
  { prefix: '├──', label: 'Market data service' },
  { prefix: '├──', label: 'Model engine loaded' },
  { prefix: '├──', label: 'Scanning universe' },
  { prefix: '├──', label: 'Syncing portfolio' },
  { prefix: '├──', label: 'Loading watchlists' },
  { prefix: '├──', label: 'Connecting market feeds' },
  { prefix: '├──', label: 'Portfolio sync' },
  { prefix: '└──', label: 'UI components ready' },
];

export function BootPhase({ active, backendReady, staggerMs = 110 }: BootPhaseProps) {
  // Track which header lines are visible (title, divider, status)
  const [visibleHeaders, setVisibleHeaders] = useState(0);
  // Track which boot lines are visible
  const [visibleLines, setVisibleLines] = useState(0);
  // Track which checkmarks are visible
  const [visibleChecks, setVisibleChecks] = useState(0);
  // Whether we've started animating checkmarks
  const [checksStarted, setChecksStarted] = useState(false);
  // Whether the completion line is visible
  const [showCompletion, setShowCompletion] = useState(false);

  // Animate header lines in: title, divider, status message
  useEffect(() => {
    if (!active) return;

    const headerCount = 3; // title, divider, "Initializing..."
    const timers: ReturnType<typeof setTimeout>[] = [];

    for (let i = 0; i < headerCount; i++) {
      timers.push(
        setTimeout(() => {
          setVisibleHeaders(i + 1);
        }, i * staggerMs)
      );
    }

    return () => timers.forEach(clearTimeout);
  }, [active, staggerMs]);

  // Animate boot lines in after headers
  useEffect(() => {
    if (!active || visibleHeaders < 3) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    const headerDelay = 40; // small gap after last header

    for (let i = 0; i < BOOT_LINES.length; i++) {
      timers.push(
        setTimeout(() => {
          setVisibleLines(i + 1);
          soundManager.playBootTick();
        }, headerDelay + i * staggerMs)
      );
    }

    return () => timers.forEach(clearTimeout);
  }, [active, visibleHeaders, staggerMs]);

  // Once all lines are visible and backend is ready, animate checkmarks
  useEffect(() => {
    if (checksStarted) return;
    if (!backendReady) return;
    if (visibleLines < BOOT_LINES.length) return;

    setChecksStarted(true);

    const timers: ReturnType<typeof setTimeout>[] = [];
    const checkStagger = 90;

    for (let i = 0; i < BOOT_LINES.length; i++) {
      timers.push(
        setTimeout(() => {
          setVisibleChecks(i + 1);
        }, i * checkStagger)
      );
    }

    // Show completion line after all checkmarks
    timers.push(
      setTimeout(() => {
        setShowCompletion(true);
        soundManager.playBootComplete();
      }, BOOT_LINES.length * checkStagger + 150)
    );

    return () => timers.forEach(clearTimeout);
  }, [backendReady, visibleLines, checksStarted]);

  const showCursor = visibleHeaders >= 3 && !showCompletion;

  return (
    <div>
      {/* Title */}
      <div
        className={`${styles.headerLine} ${visibleHeaders >= 1 ? styles.headerLineVisible : ''}`}
      >
        <span className={styles.title}>SPECTRE v2.0</span>
      </div>

      {/* Divider */}
      <div
        className={`${styles.headerLine} ${visibleHeaders >= 2 ? styles.headerLineVisible : ''}`}
      >
        <span className={styles.divider}>{'─'.repeat(31)}</span>
      </div>

      {/* Status line */}
      <div
        className={`${styles.statusLine} ${visibleHeaders >= 3 ? styles.statusLineVisible : ''}`}
      >
        Initializing core systems...{showCursor && <span className={styles.cursor}>▌</span>}
      </div>

      {/* Boot check lines */}
      {BOOT_LINES.map((line, i) => (
        <div
          key={i}
          className={`${styles.bootLine} ${i < visibleLines ? styles.bootLineVisible : ''}`}
        >
          <span className={styles.linePrefix}>{line.prefix}</span>
          <span className={styles.lineLabel}>{line.label}</span>
          <span
            className={`${styles.checkmark} ${i < visibleChecks ? styles.checkmarkVisible : ''}`}
          >
            &#10003;
          </span>
        </div>
      ))}

      {/* Completion line */}
      <div
        className={`${styles.completionLine} ${showCompletion ? styles.completionLineVisible : ''}`}
      >
        All systems online
      </div>
    </div>
  );
}
