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
      {showGrid && <div className={styles.hudGrid} />}

      <div className={`${styles.hudFrame} ${showFrame ? styles.hudFrameVisible : ''} ${phase === 'dissolve' ? styles.hudFrameDissolve : ''}`}>
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
