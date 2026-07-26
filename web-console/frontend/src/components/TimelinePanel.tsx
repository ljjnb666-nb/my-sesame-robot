import { RefreshCw } from "lucide-react";
import { TimelineResponse } from "../api/types";
import { EmptyState } from "./EmptyState";
import { TimelineEvent } from "./TimelineEvent";

type Props = {
  timeline: TimelineResponse | null;
  limit: number;
  loading: boolean;
  error: string | null;
  onLimit: (limit: number) => void;
  onRefresh: () => void;
};

export function TimelinePanel({ timeline, limit, loading, error, onLimit, onRefresh }: Props) {
  const events = timeline?.events ?? [];
  return (
    <section className="panel timeline-panel">
      <div className="panel-title">
        <h2>Timeline</h2>
        <button type="button" className="secondary-button" onClick={onRefresh}>
          <RefreshCw aria-hidden="true" />
          Refresh
        </button>
      </div>
      <label className="limit-control" htmlFor="timeline-limit">
        Limit
        <select id="timeline-limit" value={limit} onChange={(event) => onLimit(Number(event.target.value))}>
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
        </select>
      </label>
      {error && <div className="error-banner">{error}</div>}
      {loading && <div className="inline-loading">Refreshing timeline...</div>}
      <div className="timeline-list">
        {events.length ? events.map((event, index) => <TimelineEvent key={`${event.time ?? event.timestamp ?? "event"}-${index}`} event={event} />) : <EmptyState title="No timeline events yet." />}
      </div>
    </section>
  );
}
