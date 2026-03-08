import React from 'react';
import styles from './ErrorBoundary.module.css';

interface Props {
  children: React.ReactNode;
  moduleName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  showDetails: boolean;
}

function getFriendlyMessage(error: Error | null): string {
  if (!error) return 'This module encountered an unexpected issue.';
  const msg = error.message.toLowerCase();
  if (msg.includes('cannot read properties of undefined') || msg.includes('cannot read property'))
    return 'This model encountered a data issue. The required data may not be available.';
  if (msg.includes('is not a function'))
    return 'This model encountered an internal error.';
  if (msg.includes('network') || msg.includes('fetch'))
    return 'A network error occurred. Please check your connection.';
  return 'This model encountered an unexpected issue.';
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, showDetails: false };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(
      `[ErrorBoundary] Crash in ${this.props.moduleName ?? 'unknown'} module:`,
      error,
      info.componentStack,
    );
  }

  private handleReload = () => {
    this.setState({ hasError: false, error: null, showDetails: false });
  };

  private toggleDetails = () => {
    this.setState((prev) => ({ showDetails: !prev.showDetails }));
  };

  render() {
    if (this.state.hasError) {
      const friendlyMessage = getFriendlyMessage(this.state.error);
      const rawMessage = this.state.error?.message ?? 'Unknown error';

      return (
        <div className={styles.container}>
          <div className={styles.icon}>!</div>
          <div className={styles.headline}>
            Something went wrong in {this.props.moduleName ?? 'this module'}
          </div>
          <div className={styles.friendlyMsg}>{friendlyMessage}</div>
          <div className={styles.suggestion}>
            Try switching to a different model type using the selector above, or select a different ticker.
          </div>
          <button className={styles.retryBtn} onClick={this.handleReload}>
            Try Again
          </button>
          <div className={styles.detailsSection}>
            <button className={styles.detailsToggle} onClick={this.toggleDetails}>
              {this.state.showDetails ? '▾ Hide' : '▸ Show'} Technical Details
            </button>
            {this.state.showDetails && (
              <div className={styles.detail}>{rawMessage}</div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
