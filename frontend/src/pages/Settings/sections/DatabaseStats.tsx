import { useState, useEffect } from 'react';
import { api } from '../../../services/api';
import { Card } from '../../../components/ui/Card/Card';
import styles from './DatabaseStats.module.css';

interface DbInfo {
  file_size_bytes: number;
  tables: Record<string, number>;
}

interface SystemInfo {
  app_version: string;
  python_version: string;
  fastapi_version: string;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function DatabaseStats() {
  const [dbStats, setDbStats] = useState<Record<string, DbInfo>>({});
  const [sysInfo, setSysInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    api.get<Record<string, DbInfo>>('/api/v1/settings/database-stats').then(setDbStats).catch(() => {});
    api.get<SystemInfo>('/api/v1/settings/system-info').then(setSysInfo).catch(() => {});
  }, []);

  return (
    <Card>
      <p className={styles.title ?? ''}>System Information</p>
      {sysInfo && (
        <div className={styles.infoGrid ?? ''}>
          <div className={styles.infoRow ?? ''}>
            <span className={styles.infoLabel ?? ''}>App Version</span>
            <span className={styles.infoValue ?? ''}>{sysInfo.app_version}</span>
          </div>
          <div className={styles.infoRow ?? ''}>
            <span className={styles.infoLabel ?? ''}>Python</span>
            <span className={styles.infoValue ?? ''}>{sysInfo.python_version}</span>
          </div>
          <div className={styles.infoRow ?? ''}>
            <span className={styles.infoLabel ?? ''}>FastAPI</span>
            <span className={styles.infoValue ?? ''}>{sysInfo.fastapi_version}</span>
          </div>
        </div>
      )}

      <p className={styles.subtitle ?? ''}>Database Statistics</p>
      {Object.entries(dbStats).map(([name, info]) => (
        <div key={name} className={styles.dbSection ?? ''}>
          <div className={styles.dbHeader ?? ''}>
            <span className={styles.dbName ?? ''}>{name.replace('_', ' ')}</span>
            <span className={styles.dbSize ?? ''}>{formatBytes(info.file_size_bytes)}</span>
          </div>
          <table className={styles.table ?? ''}>
            <tbody>
              {Object.entries(info.tables).map(([table, count]) => (
                <tr key={table} className={styles.tableRow ?? ''}>
                  <td className={styles.tableName ?? ''}>{table}</td>
                  <td className={styles.tableCount ?? ''}>{count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </Card>
  );
}
