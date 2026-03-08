/**
 * WebSocket connection manager for live price and status channels.
 * Auto-reconnects with exponential backoff on disconnect.
 */

import { useMarketStore } from '../stores/marketStore';
import { useUIStore } from '../stores/uiStore';

import { WS_URL } from '../config';

const WS_BASE = WS_URL;
const MAX_RECONNECT_DELAY = 30000;
const INITIAL_RECONNECT_DELAY = 1000;

class WebSocketManager {
  private priceWs: WebSocket | null = null;
  private statusWs: WebSocket | null = null;
  private priceReconnectDelay = INITIAL_RECONNECT_DELAY;
  private statusReconnectDelay = INITIAL_RECONNECT_DELAY;
  private priceReconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private statusReconnectTimer: ReturnType<typeof setTimeout> | null = null;

  connectPrices(): void {
    if (this.priceWs?.readyState === WebSocket.OPEN) return;

    try {
      this.priceWs = new WebSocket(`${WS_BASE}/ws/prices`);

      this.priceWs.onopen = () => {
        this.priceReconnectDelay = INITIAL_RECONNECT_DELAY;
        useMarketStore.getState().setWsConnected(true);
      };

      this.priceWs.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'price_update') {
            useMarketStore.getState().updatePrices(msg.data);
          }
        } catch {
          // Malformed message — ignore
        }
      };

      this.priceWs.onclose = () => {
        useMarketStore.getState().setWsConnected(false);
        this.schedulePriceReconnect();
      };

      this.priceWs.onerror = () => {
        this.priceWs?.close();
      };
    } catch {
      this.schedulePriceReconnect();
    }
  }

  connectStatus(): void {
    if (this.statusWs?.readyState === WebSocket.OPEN) return;

    try {
      this.statusWs = new WebSocket(`${WS_BASE}/ws/status`);

      this.statusWs.onopen = () => {
        this.statusReconnectDelay = INITIAL_RECONNECT_DELAY;
        // Send initial ping to get status
        this.statusWs?.send('ping');
      };

      this.statusWs.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'system_status') {
            useUIStore.getState().updateSystemStatus(msg.data);
            if (msg.data.market_open !== undefined) {
              useMarketStore.getState().setMarketOpen(msg.data.market_open);
            }
          }
        } catch {
          // Malformed message — ignore
        }
      };

      this.statusWs.onclose = () => {
        this.scheduleStatusReconnect();
      };

      this.statusWs.onerror = () => {
        this.statusWs?.close();
      };
    } catch {
      this.scheduleStatusReconnect();
    }
  }

  subscribeTickers(tickers: string[]): void {
    if (this.priceWs?.readyState === WebSocket.OPEN) {
      this.priceWs.send(
        JSON.stringify({ type: 'subscribe', tickers }),
      );
    }
  }

  connectAll(): void {
    this.connectPrices();
    this.connectStatus();
  }

  disconnectAll(): void {
    if (this.priceReconnectTimer) clearTimeout(this.priceReconnectTimer);
    if (this.statusReconnectTimer) clearTimeout(this.statusReconnectTimer);
    this.priceWs?.close();
    this.statusWs?.close();
    this.priceWs = null;
    this.statusWs = null;
  }

  private schedulePriceReconnect(): void {
    this.priceReconnectTimer = setTimeout(() => {
      this.connectPrices();
    }, this.priceReconnectDelay);
    this.priceReconnectDelay = Math.min(
      this.priceReconnectDelay * 2,
      MAX_RECONNECT_DELAY,
    );
  }

  private scheduleStatusReconnect(): void {
    this.statusReconnectTimer = setTimeout(() => {
      this.connectStatus();
    }, this.statusReconnectDelay);
    this.statusReconnectDelay = Math.min(
      this.statusReconnectDelay * 2,
      MAX_RECONNECT_DELAY,
    );
  }
}

export const wsManager = new WebSocketManager();
