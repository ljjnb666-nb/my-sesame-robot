import { RobotStateResponse } from "../api/types";
import { faceLabel, motionStateLabel, robotPoseLabel, t } from "../i18n/zh-CN";

export function RobotSchematic({ state }: { state: RobotStateResponse | null }) {
  const hasFault = Boolean(state?.faults.length);
  const moving = state?.motionState === "moving" || Boolean(state?.currentCommand);
  return (
    <svg className={`robot-schematic ${hasFault ? "fault" : moving ? "moving" : ""}`} viewBox="0 0 520 260" role="img" aria-label="机器人示意图">
      <rect className="grid" width="520" height="260" rx="8" />
      <g className="robot-body">
        <rect x="155" y="88" width="210" height="74" rx="28" />
        <circle cx="180" cy="125" r="28" />
        <circle cx="340" cy="125" r="28" />
        <path d="M188 151 L130 202 L96 220" />
        <path d="M205 151 L175 211 L145 234" />
        <path d="M318 151 L380 202 L414 220" />
        <path d="M336 151 L360 212 L392 234" />
        <path d="M188 99 L130 58 L96 42" />
        <path d="M205 99 L175 48 L145 30" />
        <path d="M318 99 L380 58 L414 42" />
        <path d="M336 99 L360 48 L392 30" />
        <circle cx="94" cy="42" r="12" />
        <circle cx="144" cy="30" r="12" />
        <circle cx="414" cy="42" r="12" />
        <circle cx="392" cy="30" r="12" />
        <circle cx="96" cy="220" r="12" />
        <circle cx="145" cy="234" r="12" />
        <circle cx="414" cy="220" r="12" />
        <circle cx="392" cy="234" r="12" />
      </g>
      <text x="24" y="32">{t("robot.pose")} {robotPoseLabel(state?.robotPose)}</text>
      <text x="392" y="32">{t("robot.face")} {faceLabel(state?.currentFace)}</text>
      <text x="220" y="130">{motionStateLabel(state?.motionState)}</text>
    </svg>
  );
}
