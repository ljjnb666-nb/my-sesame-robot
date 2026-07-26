import { ApiHealthStatus } from "../hooks/useApiHealth";

export function ApiStatus({ status, error }: { status: ApiHealthStatus; error: string | null }) {
  if (status === "online") return null;
  return (
    <section className={`notice ${status === "blocked" ? "danger" : "warning"}`} aria-live="polite">
      <strong>{status === "blocked" ? "当前后端不是安全模拟器模式" : "本地 API 离线"}</strong>
      <span>{error ?? "Chat、Fault 和 Reset 控件已禁用。"}</span>
    </section>
  );
}
