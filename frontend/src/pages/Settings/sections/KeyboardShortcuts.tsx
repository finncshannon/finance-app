import { Card } from '../../../components/ui/Card/Card';
import styles from './KeyboardShortcuts.module.css';

const SHORTCUTS = [
  { keys: 'Ctrl + 1', description: 'Dashboard' },
  { keys: 'Ctrl + 2', description: 'Model Builder' },
  { keys: 'Ctrl + 3', description: 'Scanner' },
  { keys: 'Ctrl + 4', description: 'Portfolio' },
  { keys: 'Ctrl + 5', description: 'Research' },
  { keys: 'Ctrl + R', description: 'Refresh data' },
  { keys: 'Ctrl + S', description: 'Save / Apply' },
  { keys: 'Ctrl + F', description: 'Focus search' },
  { keys: 'Ctrl + E', description: 'Export' },
  { keys: 'Esc', description: 'Close modal / Cancel' },
];

export function KeyboardShortcuts() {
  return (
    <Card>
      <p className={styles.title ?? ''}>Keyboard Shortcuts</p>
      <table className={styles.table ?? ''}>
        <tbody>
          {SHORTCUTS.map((s) => (
            <tr key={s.keys} className={styles.row ?? ''}>
              <td className={styles.keysCell ?? ''}>
                <kbd className={styles.kbd ?? ''}>{s.keys}</kbd>
              </td>
              <td className={styles.descCell ?? ''}>{s.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
