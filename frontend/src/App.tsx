import { useEffect, useState, useCallback } from 'react';
import { ModuleTabBar, type ModuleId } from './components/Navigation/ModuleTabBar';
import { BootSequence } from './components/BootSequence/BootSequence';
import { useUIStore } from './stores/uiStore';
import { useSettingsStore } from './stores/settingsStore';
import { wsManager } from './services/websocket';
import { BASE_URL } from './config';
import { ErrorBoundary } from './components/ui/ErrorBoundary/ErrorBoundary';
import { DashboardPage } from './pages/DashboardPage';
import { ModelBuilderPage } from './pages/ModelBuilderPage';
import { ScannerPage } from './pages/ScannerPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { ResearchPage } from './pages/ResearchPage';
import { SettingsPage } from './pages/Settings/SettingsPage';

function DevGalleryPage() {
  const [DevGallery, setDevGallery] = useState<React.ComponentType | null>(null);
  useEffect(() => {
    import('./pages/DevGalleryPage').then((m) => setDevGallery(() => m.DevGalleryPage));
  }, []);
  return DevGallery ? <DevGallery /> : null;
}

const PAGE_MAP: Record<string, React.ComponentType> = {
  dashboard: DashboardPage,
  'model-builder': ModelBuilderPage,
  scanner: ScannerPage,
  portfolio: PortfolioPage,
  research: ResearchPage,
  settings: SettingsPage,
};

const HEALTH_URL = `${BASE_URL}/api/v1/system/health`;
const HEALTH_POLL_MS = 200;

export function App() {
  const activeModule = useUIStore((s) => s.activeModule);
  const setActiveModule = useUIStore((s) => s.setActiveModule);
  const setBackendReady = useUIStore((s) => s.setBackendReady);
  const hydrate = useSettingsStore((s) => s.hydrate);

  const [booted, setBooted] = useState(false);
  const [backendReady, setBackendReadyLocal] = useState(false);
  const [showDev, setShowDev] = useState(false);

  // Poll backend health until it responds 200
  useEffect(() => {
    if (backendReady) return;

    let cancelled = false;
    let resolved = false;

    const poll = async () => {
      while (!cancelled && !resolved) {
        try {
          const res = await fetch(HEALTH_URL);
          if (res.ok && !resolved) {
            resolved = true;
            setBackendReadyLocal(true);
            setBackendReady(true);
            return;
          }
        } catch {
          // Backend not up yet
        }
        if (!resolved) {
          await new Promise((r) => setTimeout(r, HEALTH_POLL_MS));
        }
      }
    };

    poll();
    return () => { cancelled = true; };
  }, [backendReady, setBackendReady]);

  // Once backend is ready, hydrate settings and connect WebSocket
  useEffect(() => {
    if (!backendReady) return;
    hydrate();
    wsManager.connectAll();
    return () => wsManager.disconnectAll();
  }, [backendReady, hydrate]);

  // Also listen for Electron IPC if available
  useEffect(() => {
    const api = (window as unknown as Record<string, unknown>).electronAPI as
      | { onBackendReady?: (cb: () => void) => () => void }
      | undefined;
    if (api?.onBackendReady) {
      const cleanup = api.onBackendReady(() => {
        setBackendReadyLocal(true);
        setBackendReady(true);
      });
      return cleanup;
    }
  }, [setBackendReady]);

  const handleBootComplete = useCallback(() => {
    setBooted(true);
    useUIStore.getState().setJustBooted(true);
  }, []);

  // Dev gallery: press Ctrl+Shift+D to toggle
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        setShowDev((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Boot sequence overlay (renders on top of everything)
  const showBoot = !booted;

  if (showDev) {
    return (
      <>
        <div style={{ padding: '8px 24px', background: 'var(--bg-secondary)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-primary)' }}>
            DEV GALLERY
          </span>
          <button onClick={() => setShowDev(false)} style={{ fontSize: 11, color: 'var(--text-secondary)', cursor: 'pointer' }}>
            Close (Ctrl+Shift+D)
          </button>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <DevGalleryPage />
        </div>
      </>
    );
  }

  const ActivePage = PAGE_MAP[activeModule] ?? DashboardPage;

  return (
    <>
      {showBoot && (
        <BootSequence
          backendReady={backendReady}
          onBootComplete={handleBootComplete}
        />
      )}
      {backendReady && (
        <>
          <ModuleTabBar
            activeModule={activeModule}
            onModuleChange={(id: ModuleId) => setActiveModule(id)}
          />
          <main style={{ flex: 1, overflow: 'auto' }}>
            <ErrorBoundary key={activeModule} moduleName={activeModule}>
              <ActivePage />
            </ErrorBoundary>
          </main>
        </>
      )}
    </>
  );
}
