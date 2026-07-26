import { Cpu, ShieldOff, Wifi, WifiOff } from "lucide-react";
import { HealthResponse } from "../api/types";
import { ApiHealthStatus } from "../hooks/useApiHealth";
import { runtimeModeLabel, t } from "../i18n/zh-CN";

type Props = {
  status: ApiHealthStatus;
  health: HealthResponse | null;
  error: string | null;
  onReconnect: () => void;
};

export function AppHeader({ status, health, error, onReconnect }: Props) {
  const online = status === "online";
  const apiLabel = status === "online" ? t("header.api.online") : status === "blocked" ? t("header.api.blocked") : t("header.api.offline");
  return (
    <header className="app-header">
      <div className="brand">
        <Cpu aria-hidden="true" />
        <div>
          <h1>{t("header.title")}</h1>
          <p>{t("header.subtitle")}</p>
        </div>
      </div>
      <div className="header-status" aria-live="polite">
        <span className={`status-pill ${online ? "ok" : status === "blocked" ? "danger" : "warn"}`}>
          {online ? <Wifi aria-hidden="true" /> : <WifiOff aria-hidden="true" />}
          {apiLabel}
        </span>
        <span className="status-pill" title={`Runtime mode: ${health?.runtimeMode ?? "unknown"}`}>
          运行模式：{runtimeModeLabel(health?.runtimeMode)}
        </span>
        <span className="status-pill" title={`Provider: ${health?.provider ?? "unknown"}`}>
          {health?.provider === "mock" ? t("header.provider.mock") : `模型服务：${health?.provider ?? "未知"}`}
        </span>
        <span className="status-pill">
          <ShieldOff aria-hidden="true" />
          {t("header.hardware.disabled")}
        </span>
        {!online && (
          <button type="button" className="secondary-button" onClick={onReconnect}>
            {t("header.reconnect")}
          </button>
        )}
      </div>
      {error && <div className="header-error">{error}</div>}
    </header>
  );
}
