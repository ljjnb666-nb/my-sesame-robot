import { BatteryCharging, CircleAlert, RadioTower, ShieldAlert } from "lucide-react";
import { RobotStateResponse } from "../api/types";
import {
  chargingStateLabel,
  commandLabel,
  communicationLabel,
  emergencyStopLabel,
  faceLabel,
  faultLabel,
  motionStateLabel,
  robotPoseLabel,
  runtimeModeLabel,
  t,
} from "../i18n/zh-CN";
import { EmptyState } from "./EmptyState";
import { RobotSchematic } from "./RobotSchematic";
import { StatusField } from "./StatusField";

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
        <h2>{t("panel.robot")}</h2>
        <span>{lastUpdatedAt ? lastUpdatedAt.toLocaleTimeString() : t("robot.notSynced")}</span>
      </div>
      <RobotSchematic state={state} />
      <div className="metric-grid">
        <div className="battery-box">
          <div className="metric-title">
            <BatteryCharging aria-hidden="true" />
            {t("robot.battery")}
          </div>
          <strong>{state?.batteryPercent ?? "未知"}%</strong>
          <div className="battery-track">
            <span style={{ width: `${Math.max(0, Math.min(100, battery))}%` }} />
          </div>
        </div>
        <StatusField label={t("robot.motion")} value={motionStateLabel(state?.motionState)} tone={state?.motionState === "moving" ? "warning" : "normal"} />
        <StatusField label={t("robot.command")} value={commandLabel(state?.currentCommand)} />
        <StatusField label={t("robot.face")} value={faceLabel(state?.currentFace)} />
        <StatusField label={t("robot.pose")} value={robotPoseLabel(state?.robotPose)} />
        <StatusField label={t("robot.charging")} value={chargingStateLabel(state?.chargingState)} />
        <StatusField label={t("robot.runtime")} value={runtimeModeLabel(state?.runtimeMode)} />
        <StatusField label={t("robot.communication")} value={communicationLabel(state?.communicationTimedOut)} tone={timedOut ? "danger" : "normal"} />
      </div>
      <div className={`safety-strip ${emergency ? "danger" : "ok"}`}>
        {emergency ? <ShieldAlert aria-hidden="true" /> : <RadioTower aria-hidden="true" />}
        {t("robot.emergencyStop")}：{emergencyStopLabel(state?.emergencyStopActive)}
      </div>
      <div className={`fault-list ${faults.length ? "has-faults" : ""}`}>
        <div>
          <CircleAlert aria-hidden="true" />
          {t("robot.faults")}（{faults.length}）
        </div>
        {faults.length ? faults.map((fault) => <span key={fault}>{faultLabel(fault)}</span>) : <EmptyState title={t("robot.noFaults")} />}
      </div>
    </section>
  );
}
