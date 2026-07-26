import { TimelineEvent as TimelineEventModel } from "../api/types";

function renderResult(event: TimelineEventModel): string {
  return event.resultStatus ?? event.resultState ?? event.resultCode ?? event.resultReason ?? "result available";
}

export function TimelineEvent({ event }: { event: TimelineEventModel }) {
  const severity = event.safetySeverity ?? event.resultStatus ?? event.resultState ?? "info";
  return (
    <article className="timeline-event">
      <time>{event.time ?? event.timestamp ?? "recent"}</time>
      <div>
        <span className={`event-type ${String(severity).includes("reject") ? "danger" : ""}`}>{event.eventType ?? "event"}</span>
        <strong>{event.action ?? event.fault ?? "simulator"}</strong>
        <p>{event.reason ?? renderResult(event)}</p>
        <small>
          result {renderResult(event)} · runtime {event.runtimeMode ?? "simulator"}
        </small>
      </div>
    </article>
  );
}
