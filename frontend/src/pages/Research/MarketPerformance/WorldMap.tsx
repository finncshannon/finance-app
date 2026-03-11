import { useMemo, useState, useEffect, useRef, useCallback } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
} from 'react-simple-maps';
import { geoCentroid } from 'd3-geo';
import s from './WorldMap.module.css';

const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

const SVG_W = 800;
const SVG_H = 450;
const CX = SVG_W / 2;
const CY = SVG_H / 2;
const BASE_SCALE = 200;

/* ── Globe view configs: rotate is [-lon, -lat, 0] to center on that point ── */
const GLOBE_VIEWS: Record<string, { rotate: [number, number, number]; scale: number }> = {
  'All':                  { rotate: [-20, -20, 0],   scale: BASE_SCALE },
  'Europe':               { rotate: [-6, -53, 0],    scale: 480 },
  'Asia':                 { rotate: [-116, -18, 0],   scale: 420 },
  'Americas':             { rotate: [87, -17, 0],     scale: 300 },
  'Middle East & Africa': { rotate: [-36, 1, 0],      scale: 380 },
  'Oceania':              { rotate: [-150, 32, 0],    scale: 520 },
};

/* ── 2-letter country code → UN M49 numeric ID (used by world-atlas TopoJSON) ── */
const ISO2_TO_M49: Record<string, string> = {
  // Europe
  GB: '826', DE: '276', FR: '250', IT: '380', ES: '724',
  CH: '756', SE: '752', NL: '528', NO: '578', DK: '208',
  PL: '616', GR: '300', TR: '792', AT: '040', FI: '246',
  IE: '372', BE: '056', PT: '620',
  LT: '440', LV: '428', EE: '233', RU: '643',
  // Asia
  JP: '392', CN: '156', KR: '410', HK: '344', TW: '158',
  IN: '356', SG: '702', TH: '764', ID: '360', MY: '458',
  VN: '704', PH: '608', PK: '586',
  // Americas
  US: '840', CA: '124', MX: '484', BR: '076', CL: '152',
  AR: '032', CO: '170', PE: '604', VE: '862',
  // Middle East & Africa
  IL: '376', SA: '682', AE: '784', QA: '634', KW: '414',
  ZA: '710', EG: '818', NG: '566', KE: '404', MA: '504',
  // Oceania
  AU: '036', NZ: '554',
};

/* ── Reverse lookup: M49 → ISO2 ── */
const M49_TO_ISO2: Record<string, string> = {};
for (const [iso2, m49] of Object.entries(ISO2_TO_M49)) {
  M49_TO_ISO2[m49] = iso2;
}

/* ── Label offsets: [dx, dy] from country centroid in SVG units ── */
const LABEL_OFFSETS: Record<string, [number, number]> = {
  // Europe
  ES: [-1, 19],
  PT: [-29, 0],
  GB: [-60, 42],
  IE: [-38, 10],
  CH: [-20, 23],
  FR: [-2, 7],
  NO: [-14, 6],
  SE: [0, 48],
  FI: [7, 24],
  EE: [30, -10],
  LT: [36, 9],
  LV: [32, -3],
  PL: [1, 15],
  NL: [-13, -13],
  DK: [-31, -15],
  BE: [-23, 16],
  AT: [32, 18],
  DE: [1, 17],
  IT: [3, 11],
  GR: [-4, 21],
  TR: [-3, 24],
  RU: [0, 10],
  // Asia
  PK: [-6, 11],
  IN: [0, 14],
  TH: [-2, 21],
  VN: [9, 4],
  MY: [-45, 9],
  ID: [-25, 11],
  PH: [-6, 26],
  TW: [26, 27],
  KR: [-31, 22],
  JP: [6, 26],
  CN: [66, 91],
  SG: [-26, 3],
  HK: [5, 4],
  // Americas
  US: [1, 10],
  CA: [-28, 32],
  MX: [4, 19],
  VE: [-1, 47],
  PE: [0, 51],
  BR: [3, 28],
  AR: [14, -18],
  CL: [8, -40],
  CO: [0, 0],
  CL: [0, 0],
  // Middle East & Africa
  ZA: [-18, 28],
  NG: [-8, 18],
  EG: [-3, 11],
  IL: [-25, -17],
  SA: [-4, 16],
  AE: [-8, -10],
  QA: [16, -4],
  KW: [-16, -5],
  KE: [16, 0],
  MA: [-18, 0],
  // Oceania
  AU: [-8, 13],
  NZ: [-12, 13],
};

/* ── Tower position offsets: [dx, dy] from country centroid ── */
const TOWER_OFFSETS: Record<string, [number, number]> = {
  ES: [6, -2],
  FR: [5, -12],
  GB: [1, 22],
  SE: [3, 24],
  FI: [1, 6],
  PL: [8, -4],
  DE: [5, -3],
  DK: [-4, -4],
  IT: [-10, -19],
  MY: [-60, -14],
  ID: [-19, -8],
  JP: [4, 4],
  CN: [67, 75],
  VE: [8, -7],
  RU: [0, 0],
  PE: [-3, 11],
  CL: [17, -64],
  AR: [17, -46],
  CA: [-22, 16],
};

/* ── Countries too small to fit their name — these get a leader line ── */
const NEEDS_LINE = new Set([
  'BE', 'NL', 'CH', 'DK', 'AT', 'LT', 'LV', 'EE', 'IE', 'PT',
  'SG', 'HK', 'TW',
  'IL', 'AE', 'QA', 'KW',
]);

/* ── Countries whose centroid is wrong (overseas territories etc.) — use fixed coords ── */
const LABEL_COORD_OVERRIDE: Record<string, [number, number]> = {
  FR: [2.5, 46.5],
  NO: [10, 62],
  US: [-98, 39],
  RU: [40, 56],  // Moscow area — real centroid is in Siberia
};

interface MarketItem {
  symbol: string;
  name: string;
  current_price: number;
  day_change: number;
  day_change_pct: number;
  country_code?: string;
}

interface Props {
  items: MarketItem[];
  usChange?: number;
  onCountryClick?: (item: MarketItem) => void;
  activeContinent?: string;
  loading?: boolean;
}

/* ── Check if a geographic point is on the visible hemisphere ── */
function isPointVisible(coords: [number, number], rotate: [number, number, number]): boolean {
  const [lon, lat] = coords;
  const centerLon = -rotate[0];
  const centerLat = -rotate[1];
  const dLon = (lon - centerLon) * Math.PI / 180;
  const lat1 = centerLat * Math.PI / 180;
  const lat2 = lat * Math.PI / 180;
  return Math.sin(lat1) * Math.sin(lat2) + Math.cos(lat1) * Math.cos(lat2) * Math.cos(dLon) > 0.05;
}

/* ── Smooth ease-in-out cubic ── */
function easeInOut(t: number): number {
  return t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/* ── DEV MODE — set to true to enable draggable labels + tower tuning ── */
const DEV_MODE = false;

export function WorldMap({ items, usChange, onCountryClick, activeContinent = 'All', loading = false }: Props) {
  const [tooltip, setTooltip] = useState<{ name: string; pct: number; x: number; y: number } | null>(null);
  const [rotation, setRotation] = useState<[number, number, number]>([-20, -20, 0]);
  const [globeScale, setGlobeScale] = useState(BASE_SCALE);
  const [isDragging, setIsDragging] = useState(false);
  const [towersGrown, setTowersGrown] = useState(false);

  /* ── Intro animation ── */
  // Phase: 'scanline' → 'rotate' → 'spin' → 'done'
  const [introPhase, setIntroPhase] = useState<'scanline' | 'rotate' | 'spin' | 'done'>('scanline');
  const [scanProgress, setScanProgress] = useState(0);   // 0→1 scanline width
  const [rotateProgress, setRotateProgress] = useState(0); // 0→1 line rotation (0°→90°)
  const [spinReveal, setSpinReveal] = useState(0);          // 0→1 scaleX reveal
  const introAnimRef = useRef<number>(0);
  const loadedRef = useRef(!loading);
  loadedRef.current = !loading;

  // Phase 1: scanline draws (300ms)
  useEffect(() => {
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - start) / 300, 1);
      setScanProgress(easeInOut(t));
      if (t < 1) { introAnimRef.current = requestAnimationFrame(tick); }
      else setIntroPhase('rotate');
    };
    introAnimRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(introAnimRef.current);
  }, []);

  // Phase 2: line rotates to vertical (400ms)
  useEffect(() => {
    if (introPhase !== 'rotate') return;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - start) / 400, 1);
      setRotateProgress(easeInOut(t));
      if (t < 1) { introAnimRef.current = requestAnimationFrame(tick); }
      else setIntroPhase('spin');
    };
    introAnimRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(introAnimRef.current);
  }, [introPhase]);

  const animRef = useRef<number>(0);
  const rotRef = useRef(rotation);
  rotRef.current = rotation;
  const scaleRef = useRef(globeScale);
  scaleRef.current = globeScale;
  const draggingRef = useRef(false);
  draggingRef.current = isDragging;
  const dragStartRef = useRef<{ x: number; y: number; rot: [number, number] } | null>(null);
  const continentRef = useRef(activeContinent);

  const isZoomed = activeContinent !== 'All';
  const zoomFactor = globeScale / BASE_SCALE;

  // Auto-spin function — eases in gradually (skipRamp for seamless intro handoff)
  const startSpin = useCallback((skipRamp = false) => {
    const spinStart = performance.now();
    const rampDuration = 2000;
    const maxSpeed = 0.12;

    const spin = (now: number) => {
      if (draggingRef.current || continentRef.current !== 'All') return;
      const elapsed = now - spinStart;
      const ramp = skipRamp ? 1 : Math.min(elapsed / rampDuration, 1);
      const speed = maxSpeed * easeInOut(ramp);
      setRotation(prev => [prev[0] - speed, prev[1], 0]);
      animRef.current = requestAnimationFrame(spin);
    };
    animRef.current = requestAnimationFrame(spin);
  }, []);

  // Phase 3: planet spins out of vertical line — scaleX(0→1) + spin decelerating to cruise
  useEffect(() => {
    if (introPhase !== 'spin') return;
    let prev = performance.now();
    let progress = 0;
    const duration = 1200;
    const introSpinSpeed = 0.8;              // deg/ms — fast opening spin
    const cruiseSpinSpeed = 0.12 / 16.67;    // deg/ms — matches auto-spin at 60fps

    const tick = (now: number) => {
      const dt = Math.min(now - prev, 50); // cap for stability
      prev = now;
      const isLoaded = loadedRef.current;

      // Reveal progress — slow near end if data not loaded
      let revealSpeed = 1 / duration;
      if (!isLoaded && progress >= 0.85) {
        revealSpeed *= 0.05;
      } else if (isLoaded && progress >= 0.85) {
        revealSpeed *= 1.8;
      }
      progress = Math.min(1, progress + revealSpeed * dt);

      // Reveal: scaleX 0→1 with ease-in-out
      setSpinReveal(easeInOut(progress));

      // Spin: decelerate smoothly from introSpinSpeed → cruiseSpinSpeed
      const t = easeInOut(progress);
      const spinDpms = introSpinSpeed + (cruiseSpinSpeed - introSpinSpeed) * t;
      setRotation(prev => [prev[0] - spinDpms * dt, prev[1], 0]);

      if (progress >= 1) {
        setSpinReveal(1);
        setIntroPhase('done');
        startSpin(true); // seamless handoff at cruise speed
        return;
      }
      introAnimRef.current = requestAnimationFrame(tick);
    };
    introAnimRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(introAnimRef.current);
  }, [introPhase, startSpin]);

  const introDone = introPhase === 'done';

  /* ── DEV MODE state ── */
  const [devLabelOffsets, setDevLabelOffsets] = useState<Record<string, [number, number]>>({});
  const [devTowerOffsets, setDevTowerOffsets] = useState<Record<string, [number, number]>>({});
  const devLabelDragRef = useRef<{ iso2: string; startX: number; startY: number; startOff: [number, number] } | null>(null);
  const devTowerDragRef = useRef<{ iso2: string; startX: number; startY: number; startOff: [number, number] } | null>(null);

  const getDevLabelOffset = useCallback((iso2: string): [number, number] => {
    return devLabelOffsets[iso2] ?? LABEL_OFFSETS[iso2] ?? [0, 0];
  }, [devLabelOffsets]);

  const getDevTowerOffset = useCallback((iso2: string): [number, number] => {
    return devTowerOffsets[iso2] ?? TOWER_OFFSETS[iso2] ?? [0, 0];
  }, [devTowerOffsets]);

  const onDevLabelMouseDown = useCallback((e: React.MouseEvent, iso2: string) => {
    if (!DEV_MODE) return;
    e.preventDefault();
    e.stopPropagation();
    const off = devLabelOffsets[iso2] ?? LABEL_OFFSETS[iso2] ?? [0, 0];
    devLabelDragRef.current = { iso2, startX: e.clientX, startY: e.clientY, startOff: [...off] as [number, number] };

    const onMove = (ev: MouseEvent) => {
      if (!devLabelDragRef.current) return;
      const { iso2: id, startX, startY, startOff } = devLabelDragRef.current;
      const svg = (e.target as SVGElement).closest('svg');
      const rect = svg?.getBoundingClientRect();
      const svgScale = rect ? SVG_W / rect.width : 1;
      const dx = (ev.clientX - startX) * svgScale;
      const dy = (ev.clientY - startY) * svgScale;
      setDevLabelOffsets((prev) => ({ ...prev, [id]: [startOff[0] + dx, startOff[1] + dy] }));
    };
    const onUp = () => {
      devLabelDragRef.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [devLabelOffsets]);

  const onDevTowerMouseDown = useCallback((e: React.MouseEvent, iso2: string) => {
    if (!DEV_MODE) return;
    e.preventDefault();
    e.stopPropagation();
    const off = devTowerOffsets[iso2] ?? [0, 0];
    devTowerDragRef.current = { iso2, startX: e.clientX, startY: e.clientY, startOff: [...off] as [number, number] };

    const onMove = (ev: MouseEvent) => {
      if (!devTowerDragRef.current) return;
      const { iso2: id, startX, startY, startOff } = devTowerDragRef.current;
      const svg = (e.target as SVGElement).closest('svg');
      const rect = svg?.getBoundingClientRect();
      const svgScale = rect ? SVG_W / rect.width : 1;
      const dx = (ev.clientX - startX) * svgScale;
      const dy = (ev.clientY - startY) * svgScale;
      setDevTowerOffsets((prev) => ({ ...prev, [id]: [startOff[0] + dx, startOff[1] + dy] }));
    };
    const onUp = () => {
      devTowerDragRef.current = null;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }, [devTowerOffsets]);

  // Animate rotation/scale on continent change (suppressed during intro)
  useEffect(() => {
    if (!introDone) return;
    continentRef.current = activeContinent;
    const target = GLOBE_VIEWS[activeContinent] ?? GLOBE_VIEWS['All'];
    const startScale = scaleRef.current;

    // Skip no-op after intro — auto-spin already running from Phase 3 handoff
    if (activeContinent === 'All' && Math.abs(startScale - target.scale) < 2) {
      return;
    }

    setTowersGrown(false);
    const startRot = [...rotRef.current] as [number, number, number];
    const startTime = performance.now();
    const duration = 1500;

    cancelAnimationFrame(animRef.current);

    const animate = (now: number) => {
      const t = Math.min((now - startTime) / duration, 1);
      const e = easeInOut(t);

      setRotation([
        startRot[0] + (target.rotate[0] - startRot[0]) * e,
        startRot[1] + (target.rotate[1] - startRot[1]) * e,
        0,
      ]);
      setGlobeScale(startScale + (target.scale - startScale) * e);

      if (t < 1) {
        animRef.current = requestAnimationFrame(animate);
      } else {
        if (activeContinent === 'All') {
          startSpin();
        } else {
          // Towers rise after zoom completes
          setTimeout(() => setTowersGrown(true), 50);
        }
      }
    };

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [activeContinent, introDone, startSpin]);

  // Drag to rotate (All view, or any view in dev mode)
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (!DEV_MODE && activeContinent !== 'All') return;
    e.preventDefault();
    setIsDragging(true);
    cancelAnimationFrame(animRef.current);
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      rot: [rotRef.current[0], rotRef.current[1]],
    };
  }, [activeContinent]);

  // Scroll to zoom (dev mode only)
  const onWheel = useCallback((e: React.WheelEvent) => {
    if (!DEV_MODE) return;
    e.preventDefault();
    setGlobeScale(prev => Math.max(100, Math.min(800, prev - e.deltaY * 0.5)));
  }, []);

  useEffect(() => {
    if (!isDragging) return;

    const onMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return;
      const { x, y, rot } = dragStartRef.current;
      const dx = (e.clientX - x) * 0.3;
      const dy = (e.clientY - y) * 0.3;
      setRotation([rot[0] + dx, Math.max(-70, Math.min(70, rot[1] - dy)), 0]);
    };

    const onUp = () => {
      setIsDragging(false);
      dragStartRef.current = null;
      if (continentRef.current === 'All') startSpin();
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isDragging, startSpin]);

  // Build lookup: M49 numeric id → MarketItem
  const countryMap = useMemo(() => {
    const map = new Map<string, MarketItem>();
    for (const item of items) {
      if (item.country_code) {
        const m49 = ISO2_TO_M49[item.country_code];
        if (m49) map.set(m49, item);
      }
    }
    if (usChange !== undefined) {
      map.set('840', {
        symbol: 'SPY',
        name: 'United States',
        current_price: 0,
        day_change: 0,
        day_change_pct: usChange,
        country_code: 'US',
      });
    }
    return map;
  }, [items, usChange]);

  return (
    <div
      className={s.mapContainer}
      onMouseDown={onMouseDown}
      onWheel={DEV_MODE ? onWheel : undefined}
      style={{ cursor: (activeContinent === 'All' || DEV_MODE) ? (isDragging ? 'grabbing' : 'grab') : 'default' }}
    >
      <ComposableMap
        projection="geoOrthographic"
        projectionConfig={{
          scale: globeScale,
          rotate: rotation,
        }}
        width={SVG_W}
        height={SVG_H}
        style={{ width: '100%', height: '100%' }}
      >
        <defs>
          <radialGradient id="ocean-depth" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(4, 4, 6, 0.15)" />
            <stop offset="50%" stopColor="rgba(4, 4, 6, 0.2)" />
            <stop offset="80%" stopColor="rgba(2, 2, 4, 0.7)" />
            <stop offset="95%" stopColor="rgba(1, 1, 2, 0.92)" />
            <stop offset="100%" stopColor="rgba(0, 0, 0, 0.98)" />
          </radialGradient>
        </defs>

        {/* ── Intro line visuals (rendered above globe) ── */}
        {!introDone && (
          <>
            {/* Phase 1: Horizontal scanline */}
            {introPhase === 'scanline' && (
              <line
                x1={CX - globeScale * scanProgress}
                y1={CY}
                x2={CX + globeScale * scanProgress}
                y2={CY}
                stroke="rgba(140, 140, 140, 0.7)"
                strokeWidth={1.2}
              />
            )}
            {/* Phase 2: Line rotates to vertical — stays briefly into Phase 3 as bridge */}
            {(introPhase === 'rotate' || (introPhase === 'spin' && spinReveal < 0.12)) && (
              <g transform={`rotate(${introPhase === 'rotate' ? -90 * rotateProgress : -90} ${CX} ${CY})`}>
                <line
                  x1={CX - globeScale} y1={CY}
                  x2={CX + globeScale} y2={CY}
                  stroke="rgba(140, 140, 140, 0.7)"
                  strokeWidth={1.2}
                  opacity={introPhase === 'spin' ? Math.max(0, 1 - spinReveal * 10) : 1}
                />
              </g>
            )}
          </>
        )}

        {/* Globe content — scaleX reveal during intro spin */}
        <g
          transform={!introDone && introPhase === 'spin'
            ? `translate(${CX}, 0) scale(${Math.max(0.005, spinReveal)}, 1) translate(${-CX}, 0)`
            : undefined
          }
          style={{ opacity: introDone ? 1 : introPhase === 'spin' ? 1 : 0 }}
        >
        {/* Ocean sphere */}
        <circle cx={CX} cy={CY} r={globeScale} fill="url(#ocean-depth)" />
        <Geographies geography={GEO_URL}>
          {({ geographies }) => {
            const geoElements = geographies.map((geo) => {
              const geoId = String(geo.id ?? '');
              const item = countryMap.get(geoId);
              const hasData = !!item;

              const fillColor = 'rgba(30, 30, 30, 1)';

              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill={fillColor}
                  stroke="rgba(60, 60, 60, 0.5)"
                  strokeWidth={0.4}
                  style={{
                    default: { outline: 'none' },
                    hover: {
                      outline: 'none',
                      fill: hasData ? 'rgba(59, 130, 246, 0.08)' : fillColor,
                      stroke: hasData ? 'rgba(59, 130, 246, 0.5)' : 'rgba(60, 60, 60, 0.5)',
                      strokeWidth: hasData ? 0.8 : 0.4,
                      cursor: hasData ? 'pointer' : 'default',
                    },
                    pressed: { outline: 'none' },
                  }}
                  onMouseEnter={(e) => {
                    if (!hasData) return;
                    const rect = (e.target as SVGElement).closest('svg')?.getBoundingClientRect();
                    if (rect) {
                      setTooltip({
                        name: item.name,
                        pct: item.day_change_pct,
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top,
                      });
                    }
                  }}
                  onMouseLeave={() => setTooltip(null)}
                  onClick={() => {
                    if (hasData && onCountryClick) onCountryClick(item);
                  }}
                />
              );
            });


            /* ── 3D towers + labels (zoomed view only, visible hemisphere only) ── */
            const towerElements: React.ReactNode[] = [];
            const labelElements: React.ReactNode[] = [];

            if (isZoomed) {
              let idx = 0;
              geographies
                .filter((geo) => countryMap.has(String(geo.id ?? '')))
                .forEach((geo) => {
                  const geoId = String(geo.id ?? '');
                  const iso2 = M49_TO_ISO2[geoId];
                  const item = countryMap.get(geoId);
                  if (!iso2 || !item) return;
                  const centroid = LABEL_COORD_OVERRIDE[iso2] ?? geoCentroid(geo) as [number, number];
                  if (!isPointVisible(centroid, rotation)) return;

                  const pct = item.day_change_pct * 100;
                  const absPct = Math.abs(pct);
                  const maxH = 70 / zoomFactor;
                  const minH = 6 / zoomFactor;
                  const towerH = Math.max(minH, (Math.log(1 + absPct) / Math.log(1 + 30)) * maxH);
                  const towerW = 8 / zoomFactor;
                  const isoX = 4 / zoomFactor;
                  const isoY = 2.5 / zoomFactor;
                  const isUp = pct >= 0;

                  const frontColor = isUp ? 'rgba(34, 197, 94, 0.9)' : 'rgba(239, 68, 68, 0.9)';
                  const sideColor = isUp ? 'rgba(18, 120, 55, 0.9)' : 'rgba(160, 40, 40, 0.9)';
                  const topColor = isUp ? 'rgba(60, 230, 120, 0.9)' : 'rgba(255, 100, 100, 0.9)';

                  const top = isUp ? -towerH : 0;
                  const bot = isUp ? 0 : towerH;
                  const hw = towerW / 2;
                  const scale = towersGrown ? 1 : 0;
                  const staggerDelay = idx * 0.06; // cascade effect
                  idx++;

                  const tOff = DEV_MODE ? getDevTowerOffset(iso2) : (TOWER_OFFSETS[iso2] ?? [0, 0]);

                  towerElements.push(
                    <Marker key={`tower-${geoId}`} coordinates={centroid}>
                      <g
                        transform={`translate(${tOff[0]}, ${tOff[1]})`}
                        style={{
                          transform: `translate(${tOff[0]}px, ${tOff[1]}px) scaleY(${scale})`,
                          transformOrigin: `${tOff[0]}px 0`,
                          transition: `transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) ${staggerDelay}s`,
                          cursor: DEV_MODE ? 'grab' : undefined,
                        }}
                        onMouseDown={DEV_MODE ? (e) => onDevTowerMouseDown(e, iso2) : undefined}
                      >
                        <rect x={-hw} y={top} width={towerW} height={towerH} fill={frontColor} />
                        <polygon
                          points={`${hw},${top} ${hw + isoX},${top - isoY} ${hw + isoX},${bot - isoY} ${hw},${bot}`}
                          fill={sideColor}
                        />
                        <polygon
                          points={`${-hw},${top} ${-hw + isoX},${top - isoY} ${hw + isoX},${top - isoY} ${hw},${top}`}
                          fill={topColor}
                        />
                      </g>
                    </Marker>
                  );

                  // Labels — position at tower tip, transition with tower
                  const off = DEV_MODE ? getDevLabelOffset(iso2) : (LABEL_OFFSETS[iso2] ?? [0, 0]);
                  const hasOffset = off[0] !== 0 || off[1] !== 0;
                  const showLine = hasOffset && NEEDS_LINE.has(iso2);
                  const fontSize = 13 / 1.5;
                  const gap = 4 / zoomFactor;
                  const labelY = towersGrown
                    ? (isUp ? -towerH - gap : towerH + gap)
                    : (isUp ? -gap : gap);

                  labelElements.push(
                    <Marker key={`label-${geoId}`} coordinates={centroid}>
                      <g style={{ transition: `transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) ${staggerDelay}s` }}>
                        {showLine && (
                          <line
                            x1={0} y1={labelY}
                            x2={off[0]} y2={off[1] + labelY}
                            stroke="rgba(255, 255, 255, 0.45)"
                            strokeWidth={0.4}
                          />
                        )}
                        <text
                          x={hasOffset ? off[0] : 0}
                          y={(hasOffset ? off[1] : 0) + labelY}
                          textAnchor="middle"
                          dominantBaseline="central"
                          onMouseDown={DEV_MODE ? (e) => onDevLabelMouseDown(e, iso2) : undefined}
                          style={{
                            fontFamily: 'var(--font-sans)',
                            fontSize: `${fontSize}px`,
                            fontWeight: 600,
                            fill: 'rgba(255, 255, 255, 0.9)',
                            paintOrder: 'stroke',
                            stroke: 'rgba(0, 0, 0, 0.8)',
                            strokeWidth: '0.5px',
                            letterSpacing: '0.3px',
                            pointerEvents: DEV_MODE ? 'auto' : 'none',
                            cursor: DEV_MODE ? 'grab' : undefined,
                          }}
                        >
                          {item.name}
                        </text>
                      </g>
                    </Marker>
                  );
                });
            }

            return (
              <>
                {geoElements}
                {towerElements}
                {labelElements}
              </>
            );
          }}
        </Geographies>

        {/* Globe edge ring */}
        <circle cx={CX} cy={CY} r={globeScale} fill="none" stroke="rgba(120, 120, 120, 0.18)" strokeWidth={1.2} />
        <circle cx={CX} cy={CY} r={globeScale + 2} fill="none" stroke="rgba(80, 80, 80, 0.06)" strokeWidth={2} />
        </g>
      </ComposableMap>

      {tooltip && (
        <div
          className={s.tooltip}
          style={{ left: tooltip.x, top: tooltip.y - 36 }}
        >
          <span className={s.tooltipName}>{tooltip.name}</span>
          <span
            className={s.tooltipPct}
            style={{ color: tooltip.pct >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}
          >
            {tooltip.pct >= 0 ? '+' : ''}{(tooltip.pct * 100).toFixed(2)}%
          </span>
        </div>
      )}

      {/* DEV MODE: Label offset output panel */}
      {DEV_MODE && Object.keys(devLabelOffsets).length > 0 && (
        <div style={{
          position: 'absolute', top: 4, right: 4, background: 'rgba(0,0,0,0.92)',
          border: '1px solid #444', borderRadius: 6, padding: '8px 12px',
          fontFamily: 'monospace', fontSize: 11, color: '#0f0',
          maxHeight: 300, overflowY: 'auto', zIndex: 20, whiteSpace: 'pre',
        }}>
          <div style={{ color: '#888', marginBottom: 4 }}>LABEL OFFSETS</div>
          {Object.entries(devLabelOffsets).map(([k, v]) =>
            `${k}: [${Math.round(v[0])}, ${Math.round(v[1])}],`
          ).join('\n')}
        </div>
      )}

      {/* DEV MODE: View (rotation/scale) output */}
      {DEV_MODE && (
        <div style={{
          position: 'absolute', top: 4, left: 4, background: 'rgba(0,0,0,0.92)',
          border: '1px solid #446', borderRadius: 6, padding: '8px 12px',
          fontFamily: 'monospace', fontSize: 11, color: '#8cf',
          zIndex: 20, whiteSpace: 'pre',
        }}>
          <div style={{ color: '#888', marginBottom: 4 }}>VIEW — {activeContinent}</div>
          {`rotate: [${Math.round(rotation[0])}, ${Math.round(rotation[1])}, 0]\nscale: ${Math.round(globeScale)}`}
        </div>
      )}

      {/* DEV MODE: Tower offset output panel */}
      {DEV_MODE && Object.keys(devTowerOffsets).length > 0 && (
        <div style={{
          position: 'absolute', bottom: 4, left: 4, background: 'rgba(0,0,0,0.92)',
          border: '1px solid #664', borderRadius: 6, padding: '8px 12px',
          fontFamily: 'monospace', fontSize: 11, color: '#ff0',
          maxHeight: 300, overflowY: 'auto', zIndex: 20, whiteSpace: 'pre',
        }}>
          <div style={{ color: '#888', marginBottom: 4 }}>TOWER OFFSETS</div>
          {Object.entries(devTowerOffsets).map(([k, v]) =>
            `${k}: [${Math.round(v[0])}, ${Math.round(v[1])}],`
          ).join('\n')}
        </div>
      )}
    </div>
  );
}
