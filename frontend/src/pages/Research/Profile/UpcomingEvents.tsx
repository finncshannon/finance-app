import styles from './UpcomingEvents.module.css';

interface EventItem {
  event_type: string;
  event_date: string;
  description: string;
}

interface UpcomingEventsProps {
  events: EventItem[];
}

function dotColor(eventType: string): string {
  switch (eventType) {
    case 'earnings':
      return 'var(--accent-primary)';
    case 'ex_dividend':
      return 'var(--color-positive)';
    default:
      return 'var(--text-tertiary)';
  }
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatEventType(type: string): string {
  return type
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export function UpcomingEvents({ events }: UpcomingEventsProps) {
  return (
    <div className={styles.card ?? ''}>
      <h3 className={styles.title ?? ''}>Upcoming Events</h3>
      {events.length === 0 ? (
        <p className={styles.empty ?? ''}>No upcoming events</p>
      ) : (
        <ul className={styles.list ?? ''}>
          {events.map((evt, i) => (
            <li key={i} className={styles.eventRow ?? ''}>
              <span
                className={styles.dot ?? ''}
                style={{ backgroundColor: dotColor(evt.event_type) }}
              />
              <span className={styles.date ?? ''}>{formatDate(evt.event_date)}</span>
              <span className={styles.eventType ?? ''}>{formatEventType(evt.event_type)}</span>
              <span className={styles.eventDesc ?? ''}>{evt.description}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
