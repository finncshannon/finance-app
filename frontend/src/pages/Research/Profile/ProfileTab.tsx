import type { CompanyProfile } from '../types';
import { CompanyOverview } from './CompanyOverview';
import { KeyStatsCard } from './KeyStatsCard';
import { BusinessOverview } from './BusinessOverview';
import { UpcomingEvents } from './UpcomingEvents';
import { ResearchNotes } from './ResearchNotes';
import styles from './ProfileTab.module.css';

interface ProfileTabProps {
  ticker: string;
  profile: CompanyProfile | null;
}

export function ProfileTab({ ticker, profile }: ProfileTabProps) {
  if (!profile) {
    return (
      <div className={styles.container ?? ''}>
        <p className={styles.empty ?? ''}>No profile data available</p>
      </div>
    );
  }

  return (
    <div className={styles.container ?? ''}>
      <CompanyOverview profile={profile} />
      <KeyStatsCard profile={profile} />
      <BusinessOverview ticker={ticker} />
      <UpcomingEvents events={profile.upcoming_events ?? []} />
      <ResearchNotes ticker={ticker} />
    </div>
  );
}
