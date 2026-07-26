import { TimelineEvent as TimelineEventModel } from "../api/types";
import { actionLabel, eventTypeLabel, faultLabel, resultLabel, runtimeModeLabel, t } from "../i18n/zh-CN";

function rawResultCode(event: TimelineEventModel): string | null {
  return event.resultStatus ?? event.resultState ?? event.resultCode ?? event.resultReason ?? null;
}

function renderResult(event: TimelineEventModel): string {
  return resultLabel(rawResultCode(event) ?? "result_available");
}

export function TimelineEvent({ event }: { event: TimelineEventModel }) {
  const severity = event.safetySeverity ?? event.resultStatus ?? event.resultState ?? "info";
  const title = event.fault ? faultLabel(event.fault) : event.action ? actionLabel(event.action) : t("timeline.event");
  const result = renderResult(event);
  const code = rawResultCode(event);
  return (
    <article className="timeline-event">
      <time>{event.time ?? event.timestamp ?? t("timeline.recent")}</time>
      <div>
        <span className={`event-type ${String(severity).includes("reject") ? "danger" : ""}`}>{eventTypeLabel(event.eventType)}</span>
        <strong>{title}</strong>
        <p>{event.reason ? `${t("timeline.reason")}：${event.reason}` : `${t("timeline.result")}：${result}`}</p>
        <small>
          {t("timeline.result")}：{result}
          {code ? ` · ${t("timeline.code", { code })}` : ""} · {t("timeline.runtime")}：{runtimeModeLabel(event.runtimeMode ?? "simulator")}
        </small>
      </div>
    </article>
  );
}
