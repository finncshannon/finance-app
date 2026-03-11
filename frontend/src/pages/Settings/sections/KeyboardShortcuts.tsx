import { Card } from '../../../components/ui/Card/Card';
import styles from './KeyboardShortcuts.module.css';

export function KeyboardShortcuts() {
  const mod = navigator.platform?.includes('Mac') ? 'Cmd' : 'Ctrl';

  const shortcuts = [
    { keys: `${mod} + 1`, description: 'Dashboard' },
    { keys: `${mod} + 2`, description: 'Model Builder' },
    { keys: `${mod} + 3`, description: 'Scanner' },
    { keys: `${mod} + 4`, description: 'Portfolio' },
    { keys: `${mod} + 5`, description: 'Research' },
    { keys: `${mod} + R`, description: 'Refresh data' },
    { keys: `${mod} + S`, description: 'Save / Apply' },
    { keys: `${mod} + F`, description: 'Focus search' },
    { keys: `${mod} + E`, description: 'Export' },
    { keys: 'Esc', description: 'Close modal / Cancel' },
  ];

  return (
    <Card>
      <p className={styles.title ?? ''}>Keyboard Shortcuts</p>
      <table className={styles.table ?? ''}>
        <tbody>
          {shortcuts.map((s) => (
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
