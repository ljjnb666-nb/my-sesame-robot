import { BatteryCharging, CircleAlert, RadioTower, ShieldAlert } from "lucide-react";
import { RobotStateResponse } from "../api/types";
import { StatusField } from "./StatusField";
import { RobotSchematic } from "./RobotSchematic";
import { EmptyState } from "./EmptyState";

type Props = {
  state: RobotStateResponse | null;
  lastUpdatedAt: Date | null;
};

export function RobotOverview({ state, lastUpdatedAt }: Props) {
  const battery = state?.batteryPercent ?? 0;
  const emergency = state?.emergencyStopActive === true;
  const timedOut = state?.communicationTimedOut === true;
  const faults = state?.faults ?? [];
  return (
    <section className="panel robot-overview">
      <div className="panel-title">
        <h2>Robot Overview</h2>
        <span>{lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : "not synced"}</span>
      </div>
      <RobotSchematic state={state} />
      <div className="metric-grid">
        <div className="battery-box">
          <div className="metric-title">
            <BatteryCharging aria-hidden="true" />
            Battery
          </div>
          <strong>{state?.batteryPercent ?? "unknown"}%</strong>
          <div className="battery-track">
            <span style={{ width: `${Math.max(0, Math.min(100, battery))}%` }} />
          </div>
        </div>
        <StatusField label="Motion" value={state?.motionState} tone={state?.motionState === "moving" ? "warning" : "normal"} />
        <StatusField label="Command" value={state?.currentCommand || "none"} />
        <StatusField label="Face" value={state?.currentFace} />
        <StatusField label="Pose" value={state?.robotPose} />
        <StatusField label="Charging" value={state?.chargingState} />
        <StatusField label="Runtime" value={state?.runtimeMode} />
        <StatusField label="Communication" value={timedOut ? "timeout" : "online"} tone={timedOut ? "danger" : "normal"} />
      </div>
      <div className={`safety-strip ${emergency ? "danger" : "ok"}`}>
        {emergency ? <ShieldAlert aria-hidden="true" /> : <RadioTower aria-hidden="true" />}
        Emergency stop: {emergency ? "ACTIVE" : "inactive"}
      </div>
      <div className={`fault-list ${faults.length ? "has-faults" : ""}`}>
        <div>
          <CircleAlert aria-hidden="true" />
          Faults ({faults.length})
        </div>
        {faults.length ? faults.map((fault) => <span key={fault}>{fault}</span>) : <EmptyState title="No simulator faults" />}
      </div>
    </section>
  );
}
