import { useState } from 'react';
import type { CompanyProfile } from '../types';
import { fmtNumber } from '../types';
import styles from './CompanyOverview.module.css';

interface CompanyOverviewProps {
  profile: CompanyProfile;
}

const DESC_LIMIT = 300;

export function CompanyOverview({ profile }: CompanyOverviewProps) {
  const [expanded, setExpanded] = useState(false);

  const description = profile.description ?? '';
  const needsTruncation = description.length > DESC_LIMIT;
  const displayDesc = needsTruncation && !expanded
    ? description.slice(0, DESC_LIMIT) + '...'
    : description;

  return (
    <div className={styles.card ?? ''}>
      <div className={styles.header ?? ''}>
        <div className={styles.titleBlock ?? ''}>
          <h2 className={styles.companyName ?? ''}>{profile.company_name}</h2>
          <span className={styles.subtitle ?? ''}>
            {profile.sector} &middot; {profile.industry}
          </span>
        </div>
        <span className={styles.exchangeBadge ?? ''}>{profile.exchange}</span>
      </div>

      {description && (
        <div className={styles.description ?? ''}>
          <p className={styles.descText ?? ''}>{displayDesc}</p>
          {needsTruncation && (
            <button
              className={styles.toggleBtn ?? ''}
              onClick={() => setExpanded((prev) => !prev)}
            >
              {expanded ? 'Show less' : 'Read more'}
            </button>
          )}
        </div>
      )}

      <div className={styles.detailRow ?? ''}>
        {profile.country && (
          <span className={styles.detailItem ?? ''}>{profile.country}</span>
        )}
        {profile.employees != null && (
          <span className={styles.detailItem ?? ''}>
            {fmtNumber(profile.employees)} employees
          </span>
        )}
        {profile.website && (
          <a
            className={styles.detailLink ?? ''}
            href={profile.website}
            target="_blank"
            rel="noopener noreferrer"
          >
            {profile.website.replace(/^https?:\/\//, '')}
          </a>
        )}
      </div>
    </div>
  );
}
