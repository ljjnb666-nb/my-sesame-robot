import { Battery, Bot, Clock, Hand, ListChecks, Octagon, ShieldAlert, StepForward } from "lucide-react";

const commands = [
  { label: "查看状态", text: "查看机器人状态", icon: Bot },
  { label: "查看电量", text: "查看电量", icon: Battery },
  { label: "挥手", text: "wave", icon: Hand },
  { label: "向前走", text: "walk forward", icon: StepForward },
  { label: "停止", text: "stop", icon: Octagon },
  { label: "查看故障", text: "查看故障", icon: ShieldAlert },
  { label: "查看时间线", text: "查看时间线", icon: Clock },
  { label: "安全检查", text: "查看当前安全状态", icon: ListChecks },
];

export function QuickCommands({ disabled, onSend }: { disabled: boolean; onSend: (text: string) => void }) {
  return (
    <div className="quick-commands" aria-label="常用命令">
      {commands.map(({ label, text, icon: Icon }) => (
        <button key={label} type="button" disabled={disabled} onClick={() => onSend(text)}>
          <Icon aria-hidden="true" />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}
