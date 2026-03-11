import { useState, useEffect } from 'react';
import styles from './BootSequence.module.css';
import type { BootPhase } from './BootSequence';

interface BootHUDProps {
  phase: BootPhase;
}

export function BootHUD({ phase }: BootHUDProps) {
  const [titleChars, setTitleChars] = useState(0);
  const [showVersion, setShowVersion] = useState(false);

  const title = 'SPECTRE';

  // Type out title letter by letter during identity phase
  useEffect(() => {
    if (phase !== 'identity') return;
    if (titleChars >= title.length) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = titleChars; i < title.length; i++) {
      timers.push(
        setTimeout(() => {
          setTitleChars(i + 1);
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

  const showFrame = phase !== 'black';
  const showTitle = phase === 'identity';

  return (
    <div className={`${styles.hudFrame} ${showFrame ? styles.hudFrameVisible : ''}`}>
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
    </div>
  );
}
