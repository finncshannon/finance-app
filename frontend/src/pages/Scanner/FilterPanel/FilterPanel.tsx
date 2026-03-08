import type { ScannerFilter, MetricDefinition, ScannerPreset } from '../types';
import { PresetSelector } from './PresetSelector';
import { FilterRow } from './FilterRow';
import { TextSearchInput } from './TextSearchInput';
import styles from './FilterPanel.module.css';

interface FilterPanelProps {
  metrics: MetricDefinition[];
  categories: Record<string, string[]>;
  presets: ScannerPreset[];
  filters: ScannerFilter[];
  textQuery: string;
  formTypes: string[];
  universe: string;
  onUniverseChange: (universe: string) => void;
  onFiltersChange: (filters: ScannerFilter[]) => void;
  onTextQueryChange: (q: string) => void;
  onFormTypesChange: (types: string[]) => void;
  onSelectPreset: (preset: ScannerPreset) => void;
  onDeletePreset: (id: number) => void;
  onClear: () => void;
  onSave: () => void;
}

export function FilterPanel({
  metrics,
  categories,
  presets,
  filters,
  textQuery,
  formTypes,
  universe,
  onUniverseChange,
  onFiltersChange,
  onTextQueryChange,
  onFormTypesChange,
  onSelectPreset,
  onDeletePreset,
  onClear,
  onSave,
}: FilterPanelProps) {
  const handleAddFilter = () => {
    onFiltersChange([...filters, { metric: '', operator: 'gte', value: null }]);
  };

  const handleUpdateFilter = (index: number, updated: ScannerFilter) => {
    const next = filters.map((f, i) => (i === index ? updated : f));
    onFiltersChange(next);
  };

  const handleRemoveFilter = (index: number) => {
    onFiltersChange(filters.filter((_, i) => i !== index));
  };

  return (
    <div className={styles.panel}>
      {/* Universe Selector */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>Universe</div>
        <select
          className={styles.universeSelect}
          value={universe}
          onChange={(e) => onUniverseChange(e.target.value)}
        >
          <option value="all">All Companies</option>
          <option value="dow">DOW 30</option>
          <option value="sp500">S&P 500</option>
          <option value="r3000">Russell 3000</option>
        </select>
      </div>

      <div className={styles.divider} />

      {/* Preset Selector */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>Presets</div>
        <PresetSelector
          presets={presets}
          onSelect={onSelectPreset}
          onDelete={onDeletePreset}
        />
      </div>

      <div className={styles.divider} />

      {/* Filter Rows */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>Filters</div>
        {filters.map((filter, i) => (
          <FilterRow
            key={i}
            filter={filter}
            metrics={metrics}
            categories={categories}
            onChange={(updated) => handleUpdateFilter(i, updated)}
            onRemove={() => handleRemoveFilter(i)}
          />
        ))}
        <button className={styles.addBtn} onClick={handleAddFilter} type="button">
          + Add Filter
        </button>
      </div>

      <div className={styles.divider} />

      {/* Text Search */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>Filing Search</div>
        <TextSearchInput
          value={textQuery}
          formTypes={formTypes}
          onChange={onTextQueryChange}
          onFormTypesChange={onFormTypesChange}
        />
      </div>

      <div className={styles.divider} />

      {/* Action Buttons */}
      <div className={styles.actions}>
        <button className={styles.actionBtn} onClick={onClear} type="button">
          Clear All
        </button>
        <button className={styles.actionBtn} onClick={onSave} type="button">
          Save Preset
        </button>
      </div>
    </div>
  );
}
