import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../../services/api';
import { useUIStore } from '../../../stores/uiStore';
import type { NewsArticle } from '../../Research/types';
import s from './NewsWidget.module.css';

const SCROLL_START_DELAY = 6000;
const RESUME_DELAY = 5000;

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  if (isNaN(then)) return '';
  const diffSec = Math.floor((now - then) / 1000);
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  if (diffDay === 1) return 'yesterday';
  if (diffDay < 30) return `${diffDay}d ago`;
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function getCurrentTranslateY(el: HTMLElement): number {
  const style = getComputedStyle(el);
  const matrix = style.transform;
  if (!matrix || matrix === 'none') return 0;
  // matrix(1, 0, 0, 1, tx, ty)
  const match = matrix.match(/matrix.*\((.+)\)/);
  if (!match) return 0;
  const values = match[1].split(',').map(Number);
  return values[5] ?? 0;
}

export function NewsWidget() {
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [scrollActive, setScrollActive] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const [scrollDuration, setScrollDuration] = useState(0);
  const [animPaused, setAnimPaused] = useState(false);
  const [manualOffset, setManualOffset] = useState<number | null>(null);
  const resumeTimer = useRef<ReturnType<typeof setTimeout>>();
  const contentHeight = useRef(0);

  const dashboardAnimationPlayed = useUIStore((s) => s.dashboardAnimationPlayed);

  const fetchNews = useCallback(async () => {
    try {
      const data = await api.get<{ articles: NewsArticle[] }>('/api/v1/news/top?limit=2000&days=1');
      const sorted = (data.articles ?? [])
        .sort((a, b) => new Date(b.published).getTime() - new Date(a.published).getTime());
      setArticles(sorted);
    } catch {
      // silent fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();
  }, [fetchNews]);

  // Start scroll after boot animation
  useEffect(() => {
    if (articles.length === 0) return;
    const delay = dashboardAnimationPlayed ? 500 : SCROLL_START_DELAY;
    const timer = setTimeout(() => {
      if (innerRef.current) {
        contentHeight.current = innerRef.current.scrollHeight;
        const duration = contentHeight.current / 25;
        setScrollDuration(duration);
        setScrollActive(true);
      }
    }, delay);
    return () => clearTimeout(timer);
  }, [articles, dashboardAnimationPlayed]);

  const pauseAndCapture = () => {
    if (!innerRef.current) return;
    const currentY = getCurrentTranslateY(innerRef.current);
    setAnimPaused(true);
    setManualOffset(currentY);
  };

  const scheduleResume = () => {
    clearTimeout(resumeTimer.current);
    resumeTimer.current = setTimeout(() => {
      setManualOffset(null);
      setAnimPaused(false);
    }, RESUME_DELAY);
  };

  const handleMouseEnter = () => {
    pauseAndCapture();
    clearTimeout(resumeTimer.current);
  };

  const handleMouseLeave = () => {
    scheduleResume();
  };

  // Smooth wheel scrolling with momentum
  const manualOffsetRef = useRef<number | null>(null);
  manualOffsetRef.current = manualOffset;
  const targetOffset = useRef(0);
  const smoothRaf = useRef<number>(0);

  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;

    const onWheel = (e: WheelEvent) => {
      e.stopPropagation();
      e.preventDefault();
      if (!innerRef.current) return;

      if (manualOffsetRef.current === null) {
        pauseAndCapture();
      }

      const halfHeight = contentHeight.current / 2;

      setManualOffset(prev => {
        const current = prev ?? 0;
        let next = current - e.deltaY;
        if (next < -halfHeight) next += halfHeight;
        if (next > 0) next -= halfHeight;
        return next;
      });

      scheduleResume();
    };

    el.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      el.removeEventListener('wheel', onWheel);
      cancelAnimationFrame(smoothRaf.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [articles]);

  const openInResearch = () => {
    useUIStore.getState().setActiveModule('research');
  };

  const openArticle = (link: string) => {
    window.open(link, '_blank', 'noopener');
  };

  // Determine track style
  const trackStyle: React.CSSProperties = {};
  if (scrollActive) {
    if (manualOffset !== null) {
      // Manual mode — static position, no animation
      trackStyle.transform = `translateY(${manualOffset}px)`;
      trackStyle.animation = 'none';
    } else {
      // Auto-scroll mode
      trackStyle.animationDuration = `${scrollDuration}s`;
      trackStyle.animationPlayState = animPaused ? 'paused' : 'running';
    }
  }

  return (
    <div className={s.widget}>
      <div className={s.header}>
        <h3 className={s.headerTitle}>News</h3>
        <span className={s.liveTag}>LIVE</span>
        <button className={s.headerAction} onClick={openInResearch}>
          View All
        </button>
      </div>
      <div
        className={s.body}
        ref={bodyRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <div
          ref={innerRef}
          className={s.scrollTrack}
          style={trackStyle}
        >
          {loading && <div className={s.loading}>Loading news...</div>}
          {!loading && articles.length === 0 && (
            <div className={s.empty}>No recent news</div>
          )}
          {[0, 1].map(copy =>
            articles.map((article, i) => (
              <div
                key={`${copy}-${article.link}-${i}`}
                className={s.articleRow}
                onClick={() => openArticle(article.link)}
              >
                <div className={s.meta}>
                  <span className={s.source}>{article.source}</span>
                  <span className={s.dot}>&bull;</span>
                  <span>{timeAgo(article.published)}</span>
                  {article.tags && article.tags.length > 0 && article.tags.map((tag) => (
                    <span key={tag} className={s.tag}>{tag}</span>
                  ))}
                  {article.category && article.category !== 'General' && (
                    <>
                      <span className={s.dot}>&bull;</span>
                      <span className={s.category}>{article.category}</span>
                    </>
                  )}
                </div>
                <div className={s.headline}>{article.title}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
