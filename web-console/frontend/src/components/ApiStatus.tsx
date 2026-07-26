import { ApiHealthStatus } from "../hooks/useApiHealth";

export function ApiStatus({ status, error }: { status: ApiHealthStatus; error: string | null }) {
  if (status === "online") return null;
  return (
    <section className={`notice ${status === "blocked" ? "danger" : "warning"}`} aria-live="polite">
      <strong>{status === "blocked" ? "当前后端不是安全的本地模拟器模式" : "本地接口离线"}</strong>
      <span>{error ?? "对话、故障注入和重置控件已禁用。"}</span>
    </section>
  );
}
