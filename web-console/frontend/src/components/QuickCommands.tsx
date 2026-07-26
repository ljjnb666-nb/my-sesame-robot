import { Battery, Bot, Clock, Hand, ListChecks, Octagon, ShieldAlert, StepForward } from "lucide-react";
import { t } from "../i18n/zh-CN";

const commands = [
  { label: t("quick.status"), text: "查看机器人状态", icon: Bot },
  { label: t("quick.battery"), text: "查看电量", icon: Battery },
  { label: t("quick.wave"), text: "wave", icon: Hand },
  { label: t("quick.walk"), text: "walk forward", icon: StepForward },
  { label: t("quick.stop"), text: "stop", icon: Octagon },
  { label: t("quick.faults"), text: "查看故障", icon: ShieldAlert },
  { label: t("quick.timeline"), text: "查看运行记录", icon: Clock },
  { label: t("quick.safety"), text: "查看当前安全状态", icon: ListChecks },
];

export function QuickCommands({ disabled, onSend }: { disabled: boolean; onSend: (text: string) => void }) {
  return (
    <div className="quick-commands" aria-label="常用指令">
      {commands.map(({ label, text, icon: Icon }) => (
        <button key={label} type="button" disabled={disabled} onClick={() => onSend(text)}>
          <Icon aria-hidden="true" />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}
