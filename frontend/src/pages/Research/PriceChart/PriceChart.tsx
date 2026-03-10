import { useState } from 'react';
import { PriceChartLW } from './PriceChartLW';
import { PriceChartTV } from './PriceChartTV';
import styles from './PriceChart.module.css';

type ChartSource = 'custom' | 'tradingview';

interface Props {
  ticker: string;
}

export function PriceChart({ ticker }: Props) {
  const [source, setSource] = useState<ChartSource>('custom');

  return (
    <div className={styles.fullPage}>
      {/* Source toggle */}
      <div className={styles.sourceBar}>
        <div className={styles.sourceToggle}>
          <button
            className={`${styles.sourceBtn} ${source === 'custom' ? styles.sourceBtnActive : ''}`}
            onClick={() => setSource('custom')}
          >
            Chart
          </button>
          <button
            className={`${styles.sourceBtn} ${source === 'tradingview' ? styles.sourceBtnActive : ''}`}
            onClick={() => setSource('tradingview')}
          >
            TradingView
          </button>
        </div>
      </div>

      {/* Chart content */}
      <div className={styles.chartContent}>
        {source === 'custom' ? (
          <PriceChartLW ticker={ticker} />
        ) : (
          <PriceChartTV ticker={ticker} />
        )}
      </div>
    </div>
  );
}
