/**
 * TradingView Advanced Chart widget embed.
 *
 * ISOLATED — uses TradingView's own data, not the app backend.
 * To remove: delete this file and remove the "TradingView" toggle from PriceChart.tsx.
 */
import { useEffect, useRef } from 'react';
import styles from './PriceChartTV.module.css';

interface Props {
  ticker: string;
}

declare global {
  interface Window {
    TradingView?: {
      widget: new (config: Record<string, unknown>) => unknown;
    };
  }
}

export function PriceChartTV({ ticker }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetRef = useRef<unknown>(null);

  useEffect(() => {
    if (!containerRef.current || !ticker) return;

    // Clear previous widget
    containerRef.current.innerHTML = '';
    widgetRef.current = null;

    // Load TradingView script if not already loaded
    const scriptId = 'tradingview-widget-script';
    let script = document.getElementById(scriptId) as HTMLScriptElement | null;

    const initWidget = () => {
      if (!containerRef.current || !window.TradingView) return;

      // Create a unique container ID for this instance
      const containerId = `tv-chart-${Date.now()}`;
      const el = document.createElement('div');
      el.id = containerId;
      el.style.width = '100%';
      el.style.height = '100%';
      containerRef.current.appendChild(el);

      widgetRef.current = new window.TradingView.widget({
        container_id: containerId,
        symbol: ticker,
        interval: 'D',
        timezone: 'America/New_York',
        theme: 'dark',
        style: '1', // Candlestick
        locale: 'en',
        toolbar_bg: '#141414',
        enable_publishing: false,
        allow_symbol_change: false,
        hide_top_toolbar: false,
        hide_legend: false,
        save_image: false,
        withdateranges: true,
        details: false,
        hotlist: false,
        calendar: false,
        width: '100%',
        height: '100%',
        backgroundColor: '#141414',
        gridColor: '#1E1E1E',
        autosize: true,
        studies: [],
        overrides: {
          'mainSeriesProperties.candleStyle.upColor': '#22C55E',
          'mainSeriesProperties.candleStyle.downColor': '#EF4444',
          'mainSeriesProperties.candleStyle.borderUpColor': '#22C55E',
          'mainSeriesProperties.candleStyle.borderDownColor': '#EF4444',
          'mainSeriesProperties.candleStyle.wickUpColor': '#22C55E',
          'mainSeriesProperties.candleStyle.wickDownColor': '#EF4444',
          'paneProperties.background': '#141414',
          'paneProperties.vertGridProperties.color': '#1E1E1E',
          'paneProperties.horzGridProperties.color': '#1E1E1E',
          'scalesProperties.textColor': '#A3A3A3',
          'scalesProperties.lineColor': '#262626',
        },
      });
    };

    if (script && window.TradingView) {
      initWidget();
    } else if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://s3.tradingview.com/tv.js';
      script.async = true;
      script.onload = initWidget;
      document.head.appendChild(script);
    } else {
      // Script exists but not loaded yet
      script.addEventListener('load', initWidget);
    }

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = '';
      }
      widgetRef.current = null;
    };
  }, [ticker]);

  return (
    <div className={styles.wrapper}>
      <div ref={containerRef} className={styles.container} />
    </div>
  );
}
