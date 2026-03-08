import { useState } from 'react';
import { Button } from '../components/ui/Button/Button';
import { Card } from '../components/ui/Card/Card';
import { DataTable, type Column } from '../components/ui/DataTable/DataTable';
import { TickerHeaderBar } from '../components/ui/TickerHeaderBar/TickerHeaderBar';
import { LoadingSpinner } from '../components/ui/Loading/LoadingSpinner';
import { LoadingBar } from '../components/ui/Loading/LoadingBar';
import { EmptyState } from '../components/ui/EmptyState/EmptyState';
import { Input } from '../components/ui/Input/Input';
import { Select } from '../components/ui/Input/Select';
import { Checkbox } from '../components/ui/Input/Checkbox';
import { Modal } from '../components/ui/Modal/Modal';
import { Tabs } from '../components/ui/Tabs/Tabs';
import { Tooltip } from '../components/ui/Tooltip/Tooltip';

const SAMPLE_COLUMNS: Column[] = [
  { key: 'ticker', label: 'Ticker', align: 'left', sortable: true },
  { key: 'price', label: 'Price', sortable: true, format: (v) => `$${(v as number).toFixed(2)}` },
  { key: 'change', label: 'Chg%', sortable: true, format: (v) => `${(v as number).toFixed(2)}%` },
  { key: 'volume', label: 'Volume', sortable: true, format: (v) => (v as number).toLocaleString() },
  { key: 'pe', label: 'P/E', sortable: true, format: (v) => (v as number).toFixed(1) },
];

const SAMPLE_DATA = [
  { ticker: 'AAPL', price: 178.72, change: 1.23, volume: 52413000, pe: 28.4 },
  { ticker: 'MSFT', price: 415.56, change: -0.45, volume: 21879000, pe: 35.1 },
  { ticker: 'GOOGL', price: 141.80, change: 0.87, volume: 18234000, pe: 23.7 },
  { ticker: 'AMZN', price: 185.63, change: -1.12, volume: 34521000, pe: 62.3 },
  { ticker: 'NVDA', price: 875.28, change: 3.45, volume: 41287000, pe: 68.9 },
];

const SECTION_STYLE: React.CSSProperties = {
  marginBottom: 'var(--space-8)',
};

const LABEL_STYLE: React.CSSProperties = {
  fontSize: 14,
  fontWeight: 600,
  color: 'var(--text-primary)',
  marginBottom: 'var(--space-3)',
};

const SUB_STYLE: React.CSSProperties = {
  fontSize: 11,
  color: 'var(--text-tertiary)',
  marginBottom: 'var(--space-4)',
};

const ROW_STYLE: React.CSSProperties = {
  display: 'flex',
  gap: 'var(--space-3)',
  alignItems: 'center',
  flexWrap: 'wrap',
};

export function DevGalleryPage() {
  const [inputVal, setInputVal] = useState('');
  const [numVal, setNumVal] = useState('42.50');
  const [selectVal, setSelectVal] = useState('dcf');
  const [checkA, setCheckA] = useState(true);
  const [checkB, setCheckB] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [progress, setProgress] = useState(65);

  return (
    <div style={{ padding: 'var(--space-6)', maxWidth: 960 }}>
      {/* 1. Buttons */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>1. Button</div>
        <div style={SUB_STYLE}>Primary, Secondary, Danger + Disabled states</div>
        <div style={ROW_STYLE}>
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="danger">Danger</Button>
          <Button disabled>Disabled</Button>
          <Button variant="secondary" disabled>Disabled Sec</Button>
        </div>
      </div>

      {/* 2. Card */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>2. Card</div>
        <div style={SUB_STYLE}>With header, without header, clickable</div>
        <div style={{ ...ROW_STYLE, alignItems: 'flex-start' }}>
          <Card header="With Header" className="">
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>
              Card content goes here. Uses --bg-secondary background.
            </p>
          </Card>
          <Card>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>
              No header variant. Clean content area.
            </p>
          </Card>
          <Card header="Clickable" onClick={() => alert('Card clicked')}>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>
              Click me — cursor changes on hover.
            </p>
          </Card>
        </div>
      </div>

      {/* 3. DataTable */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>3. DataTable</div>
        <div style={SUB_STYLE}>Bloomberg-style with sorting. Click column headers to sort.</div>
        <DataTable columns={SAMPLE_COLUMNS} data={SAMPLE_DATA} />
      </div>

      {/* 4. TickerHeaderBar */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>4. TickerHeaderBar</div>
        <div style={SUB_STYLE}>Full ticker identity bar with price, stats, and navigation</div>
        <TickerHeaderBar
          ticker="AAPL"
          companyName="Apple Inc."
          sector="Technology"
          industry="Consumer Electronics"
          exchange="NASDAQ"
          price={178.72}
          dayChange={2.34}
          dayChangePct={1.33}
          volume={52413000}
          marketCap={2780000000000}
          onNavigate={(t) => alert(`Navigate: ${t}`)}
        />
        <div style={{ marginTop: 'var(--space-3)' }}>
          <TickerHeaderBar
            ticker="XOM"
            companyName="Exxon Mobil Corporation"
            sector="Energy"
            exchange="NYSE"
            price={104.56}
            dayChange={-1.82}
            dayChangePct={-1.71}
            onNavigate={(t) => alert(`Navigate: ${t}`)}
          />
        </div>
      </div>

      {/* 5. Loading */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>5. Loading</div>
        <div style={SUB_STYLE}>Spinner (inline) and progress bar (standalone demo)</div>
        <div style={ROW_STYLE}>
          <LoadingSpinner />
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Spinner</span>
        </div>
        <div style={{ marginTop: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Progress: {progress}%</span>
            <Button variant="secondary" onClick={() => setProgress((p) => Math.max(0, p - 10))}>-10</Button>
            <Button variant="secondary" onClick={() => setProgress((p) => Math.min(100, p + 10))}>+10</Button>
          </div>
          <div style={{ position: 'relative', height: 100, background: 'var(--bg-primary)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
            <LoadingBar progress={progress} title="Loading Model" subtitle="Fetching assumptions..." status={`${progress}% complete`} />
          </div>
        </div>
      </div>

      {/* 6. EmptyState */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>6. EmptyState</div>
        <div style={SUB_STYLE}>With and without CTA button</div>
        <div style={{ ...ROW_STYLE, alignItems: 'flex-start' }}>
          <div style={{ flex: 1, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
            <EmptyState
              headline="No positions yet"
              subtext="Add your first holding to get started"
              ctaLabel="Add Position"
              onCta={() => alert('Add position')}
            />
          </div>
          <div style={{ flex: 1, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', padding: 'var(--space-4)' }}>
            <EmptyState
              headline="No scan results"
              subtext="Adjust your filters or run a new scan"
            />
          </div>
        </div>
      </div>

      {/* 7. Input / Select / Checkbox */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>7. Input / Select / Checkbox</div>
        <div style={SUB_STYLE}>Text input, mono numeric, select dropdown, checkboxes</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-4)', maxWidth: 600 }}>
          <Input label="Company" value={inputVal} onChange={setInputVal} placeholder="Search..." />
          <Input label="Discount Rate" value={numVal} onChange={setNumVal} mono placeholder="0.00" />
          <Select
            label="Model Type"
            value={selectVal}
            onChange={setSelectVal}
            options={[
              { value: 'dcf', label: 'DCF' },
              { value: 'ddm', label: 'DDM' },
              { value: 'nav', label: 'NAV' },
              { value: 'comps', label: 'Comps' },
            ]}
          />
        </div>
        <div style={{ ...ROW_STYLE, marginTop: 'var(--space-4)' }}>
          <Checkbox label="Include options" checked={checkA} onChange={setCheckA} />
          <Checkbox label="Terminal growth" checked={checkB} onChange={setCheckB} />
          <Checkbox label="Disabled" checked={false} onChange={() => {}} disabled />
        </div>
      </div>

      {/* 8. Modal */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>8. Modal</div>
        <div style={SUB_STYLE}>Dialog with header, body, footer. Closes on ESC or overlay click.</div>
        <Button onClick={() => setModalOpen(true)}>Open Modal</Button>
        <Modal
          isOpen={modalOpen}
          onClose={() => setModalOpen(false)}
          title="Confirm Action"
          footer={
            <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
              <Button variant="secondary" onClick={() => setModalOpen(false)}>Cancel</Button>
              <Button onClick={() => setModalOpen(false)}>Confirm</Button>
            </div>
          }
        >
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0 }}>
            Are you sure you want to delete this model? This action cannot be undone.
          </p>
        </Modal>
      </div>

      {/* 9. Tabs */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>9. Tabs</div>
        <div style={SUB_STYLE}>Tier 2/3 sub-navigation tabs</div>
        <Tabs
          tabs={[
            { id: 'overview', label: 'Overview' },
            { id: 'financials', label: 'Financials' },
            { id: 'filings', label: 'Filings' },
            { id: 'notes', label: 'Notes' },
          ]}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
        <div style={{ padding: 'var(--space-4)', fontSize: 12, color: 'var(--text-secondary)' }}>
          Active: <strong>{activeTab}</strong>
        </div>
      </div>

      {/* 10. Tooltip */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>10. Tooltip</div>
        <div style={SUB_STYLE}>Hover 500ms to reveal. Positioned above trigger.</div>
        <div style={ROW_STYLE}>
          <Tooltip content="Enterprise Value / EBITDA ratio">
            <span style={{ fontSize: 12, color: 'var(--accent-primary)', cursor: 'help', borderBottom: '1px dashed var(--accent-primary)' }}>
              EV/EBITDA
            </span>
          </Tooltip>
          <Tooltip content="Weighted Average Cost of Capital — the discount rate used in DCF models">
            <span style={{ fontSize: 12, color: 'var(--accent-primary)', cursor: 'help', borderBottom: '1px dashed var(--accent-primary)' }}>
              WACC
            </span>
          </Tooltip>
          <Tooltip content="Free Cash Flow to Equity — cash available to shareholders after all obligations">
            <span style={{ fontSize: 12, color: 'var(--accent-primary)', cursor: 'help', borderBottom: '1px dashed var(--accent-primary)' }}>
              FCFE
            </span>
          </Tooltip>
        </div>
      </div>
    </div>
  );
}
