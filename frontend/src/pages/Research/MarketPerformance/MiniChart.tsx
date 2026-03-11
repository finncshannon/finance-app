import { useEffect, useRef } from 'react';
import {
  createChart,
  LineSeries,
  type IChartApi,
  type Time,
  ColorType,
  CrosshairMode,
} from 'lightweight-charts';
import { api } from '../../../services/api';

interface PriceBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface Props {
  symbol: string;
  height?: number;
}

function parseTime(dateStr: string): Time {
  if (dateStr.includes(' ')) {
    return Math.floor(new Date(dateStr.replace(' ', 'T')).getTime() / 1000) as Time;
  }
  return dateStr as Time;
}

export function MiniChart({ symbol, height = 180 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      width: el.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'rgba(255,255,255,0.4)',
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      crosshair: {
        mode: CrosshairMode.Magnet,
        vertLine: { color: 'rgba(59,130,246,0.3)', width: 1, labelVisible: false },
        horzLine: { color: 'rgba(59,130,246,0.3)', width: 1, labelVisible: true },
      },
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      timeScale: {
        borderVisible: false,
        timeVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      handleScale: false,
      handleScroll: false,
    });

    chartRef.current = chart;

    const lineSeries = chart.addSeries(LineSeries, {
      color: '#3B82F6',
      lineWidth: 2,
      crosshairMarkerRadius: 4,
      crosshairMarkerBackgroundColor: '#3B82F6',
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // Fetch data — api.get unwraps the envelope, returns PriceBar[] directly
    api.get<PriceBar[]>(
      `/api/v1/companies/${encodeURIComponent(symbol)}/historical?period=3mo&interval=1d`
    )
      .then((bars) => {
        if (!Array.isArray(bars) || bars.length === 0) return;

        const lineData = bars.map((b) => ({
          time: parseTime(b.date),
          value: b.close,
        }));

        lineSeries.setData(lineData);
        chart.timeScale().fitContent();
      })
      .catch(() => {});

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [symbol, height]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: `${height}px`,
        borderRadius: '0 0 8px 8px',
      }}
    />
  );
}
