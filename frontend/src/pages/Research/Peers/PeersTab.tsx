import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../services/api';
import { useResearchStore } from '../../../stores/researchStore';
import type { PeerCompany, CompanyProfile, RatioData } from '../types';
import { PeerSelector } from './PeerSelector';
import { PeerTable, type PeerRow } from './PeerTable';
import styles from './PeersTab.module.css';

interface PeersTabProps {
  ticker: string;
}

/** Build a PeerRow from profile + ratios data. */
function buildRow(
  ticker: string,
  name: string,
  isTarget: boolean,
  profile: CompanyProfile | null,
  ratios: RatioData | null,
): PeerRow {
  return {
    ticker,
    company_name: name,
    isTarget,
    market_cap: profile?.quote?.market_cap ?? null,
    revenue_growth: ratios?.growth?.revenue_growth_yoy ?? null,
    operating_margin: ratios?.profitability?.operating_margin ?? null,
    roe: ratios?.returns?.roe ?? null,
    pe_ratio: ratios?.valuation?.pe_ratio ?? null,
    ev_to_ebitda: ratios?.valuation?.ev_to_ebitda ?? null,
  };
}

/** Build a PeerRow from the PeerCompany data + fetched ratios. */
function buildPeerRow(peer: PeerCompany, ratios: RatioData | null): PeerRow {
  return {
    ticker: peer.ticker,
    company_name: peer.company_name ?? peer.ticker,
    isTarget: false,
    market_cap: peer.market_cap,
    revenue_growth: ratios?.growth?.revenue_growth_yoy ?? null,
    operating_margin: ratios?.profitability?.operating_margin ?? null,
    roe: ratios?.returns?.roe ?? null,
    pe_ratio: ratios?.valuation?.pe_ratio ?? peer.pe_ratio,
    ev_to_ebitda: ratios?.valuation?.ev_to_ebitda ?? null,
  };
}

export function PeersTab({ ticker }: PeersTabProps) {
  const [targetRow, setTargetRow] = useState<PeerRow | null>(null);
  const [peers, setPeers] = useState<PeerRow[]>([]);
  const [loading, setLoading] = useState(false);

  // Load target + auto-suggested peers on ticker change
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setTargetRow(null);
      setPeers([]);

      try {
        // Fetch target data and peer list in parallel
        const [profileRes, ratiosRes, peersRes] = await Promise.all([
          api.get<CompanyProfile>(`/api/v1/research/${ticker}/profile`),
          api.get<RatioData>(`/api/v1/research/${ticker}/ratios`),
          api.get<{ peers: PeerCompany[] }>(`/api/v1/research/${ticker}/peers`),
        ]);

        if (cancelled) return;

        // Build target row
        const target = buildRow(
          ticker,
          profileRes.company_name ?? ticker,
          true,
          profileRes,
          ratiosRes,
        );
        setTargetRow(target);

        // Fetch ratios for each peer
        const peerList = peersRes.peers ?? [];
        const ratioResults = await Promise.allSettled(
          peerList.map((p) => api.get<RatioData>(`/api/v1/research/${p.ticker}/ratios`)),
        );

        if (cancelled) return;

        const peerRows = peerList.map((p, i) => {
          const result = ratioResults[i];
          const peerRatios = result && result.status === 'fulfilled' ? result.value : null;
          return buildPeerRow(p, peerRatios);
        });

        setPeers(peerRows);
      } catch {
        // Silent fail — empty state shown
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [ticker]);

  // Add a custom peer
  const handleAddPeer = useCallback(async (newTicker: string) => {
    try {
      const [profile, ratios] = await Promise.all([
        api.get<CompanyProfile>(`/api/v1/research/${newTicker}/profile`),
        api.get<RatioData>(`/api/v1/research/${newTicker}/ratios`),
      ]);
      const row = buildRow(
        newTicker,
        profile.company_name ?? newTicker,
        false,
        profile,
        ratios,
      );
      setPeers((prev) => [...prev, row]);
    } catch {
      // Validation already handled in PeerSelector
    }
  }, []);

  // Remove a peer
  const handleRemove = useCallback((t: string) => {
    setPeers((prev) => prev.filter((p) => p.ticker !== t));
  }, []);

  // Navigate to a peer
  const handleNavigate = useCallback((peerTicker: string) => {
    useResearchStore.getState().setSelectedTicker(peerTicker);
  }, []);

  // All tickers currently in the table (for duplicate check in PeerSelector)
  const existingTickers = [
    ticker,
    ...peers.map((p) => p.ticker),
  ];

  // Combined rows: target first, then peers
  const allRows = targetRow ? [targetRow, ...peers] : peers;

  if (loading) {
    return <div className={styles.loading ?? ''}>Loading peer comparison...</div>;
  }

  return (
    <div className={styles.container ?? ''}>
      <PeerSelector onAdd={handleAddPeer} existingTickers={existingTickers} />
      {allRows.length > 0 ? (
        <PeerTable rows={allRows} onRemove={handleRemove} onNavigate={handleNavigate} />
      ) : (
        <div className={styles.empty ?? ''}>No peer data available</div>
      )}
    </div>
  );
}
