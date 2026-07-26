import { TimelineEvent as TimelineEventModel } from "../api/types";

function renderResult(result: TimelineEventModel["result"]): string {
  if (!result) return "none";
  if (typeof result === "string") return result;
  const safeEntries = Object.entries(result).filter(([key]) => !/confirmation|memory|path|traceback/i.test(key));
  return safeEntries.map(([key, value]) => `${key}: ${String(value)}`).join(", ");
}

export function TimelineEvent({ event }: { event: TimelineEventModel }) {
  const severity = event.safetySeverity ?? event.result ?? "info";
  return (
    <article className="timeline-event">
      <time>{event.time ?? event.timestamp ?? "recent"}</time>
      <div>
        <span className={`event-type ${String(severity).includes("reject") ? "danger" : ""}`}>{event.eventType ?? "event"}</span>
        <strong>{event.action ?? event.fault ?? "simulator"}</strong>
        <p>{event.reason ?? renderResult(event.result)}</p>
        <small>
          result {renderResult(event.result)} · runtime {event.runtimeMode ?? "simulator"}
        </small>
      </div>
    </article>
  );
}
