import { Cpu, ShieldOff, Wifi, WifiOff } from "lucide-react";
import { ApiHealthStatus } from "../hooks/useApiHealth";
import { HealthResponse } from "../api/types";

type Props = {
  status: ApiHealthStatus;
  health: HealthResponse | null;
  error: string | null;
  onReconnect: () => void;
};

export function AppHeader({ status, health, error, onReconnect }: Props) {
  const online = status === "online";
  return (
    <header className="app-header">
      <div className="brand">
        <Cpu aria-hidden="true" />
        <div>
          <h1>Sesame Robot Simulator</h1>
          <p>LOCAL SIMULATOR · REAL HARDWARE DISABLED</p>
        </div>
      </div>
      <div className="header-status" aria-live="polite">
        <span className={`status-pill ${online ? "ok" : status === "blocked" ? "danger" : "warn"}`}>
          {online ? <Wifi aria-hidden="true" /> : <WifiOff aria-hidden="true" />}
          API {status.toUpperCase()}
        </span>
        <span className="status-pill">Runtime {health?.runtimeMode ?? "unknown"}</span>
        <span className="status-pill">Provider {health?.provider ?? "unknown"}</span>
        <span className="status-pill">
          <ShieldOff aria-hidden="true" />
          Hardware disabled
        </span>
        {!online && (
          <button type="button" className="secondary-button" onClick={onReconnect}>
            Reconnect
          </button>
        )}
      </div>
      {error && <div className="header-error">{error}</div>}
    </header>
  );
}
