import { FormEvent, useState } from "react";
import { RotateCcw, Trash2, Zap } from "lucide-react";
import { ErrorBanner } from "./ErrorBanner";

type Props = {
  disabled: boolean;
  faults: string[];
  onInject: (fault: string) => Promise<void>;
  onClear: (fault: string) => Promise<void>;
  onClearAll: () => Promise<void>;
  onResetSimulator: () => Promise<void>;
  onResetSession: () => Promise<void>;
};

const suggestions = ["servo_stuck", "battery_low", "communication_lost"];

export function SimulatorControls({ disabled, faults, onInject, onClear, onClearAll, onResetSimulator, onResetSession }: Props) {
  const [fault, setFault] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Simulator 操作失败。");
    } finally {
      setBusy(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = fault.trim();
    if (!trimmed || trimmed.length > 80) return;
    void run(async () => {
      await onInject(trimmed);
      setFault("");
    });
  };

  return (
    <section className="panel simulator-controls">
      <div className="panel-title">
        <h2>Simulator Controls</h2>
        <span>Backend allowlist decides support</span>
      </div>
      <ErrorBanner message={error} />
      <form className="fault-form" onSubmit={submit}>
        <label htmlFor="fault-input">Fault injection</label>
        <div className="fault-row">
          <input
            id="fault-input"
            list="fault-suggestions"
            value={fault}
            maxLength={80}
            disabled={disabled || busy}
            onChange={(event) => setFault(event.target.value)}
            placeholder="battery_low"
          />
          <button type="submit" disabled={disabled || busy || !fault.trim()}>
            <Zap aria-hidden="true" />
            Inject
          </button>
        </div>
        <datalist id="fault-suggestions">
          {suggestions.map((item) => (
            <option key={item} value={item} />
          ))}
        </datalist>
      </form>
      <div className="fault-actions">
        {faults.map((item) => (
          <button key={item} type="button" className="secondary-button" disabled={disabled || busy} onClick={() => void run(() => onClear(item))}>
            <Trash2 aria-hidden="true" />
            Clear {item}
          </button>
        ))}
        <button type="button" className="secondary-button" disabled={disabled || busy} onClick={() => void run(onClearAll)}>
          <Trash2 aria-hidden="true" />
          Clear all faults
        </button>
      </div>
      <div className="reset-actions">
        <button
          type="button"
          className="danger-button"
          disabled={disabled || busy}
          onClick={() => {
            if (window.confirm("清空当前模拟器状态、清空 Web pending confirmation，使旧 confirmation 失效，并保留 MemoryManager。")) {
              void run(onResetSimulator);
            }
          }}
        >
          <RotateCcw aria-hidden="true" />
          Reset simulator
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={disabled || busy}
          onClick={() => {
            if (window.confirm("清空当前对话和 short-term memory，保留模拟器硬件状态。")) {
              void run(onResetSession);
            }
          }}
        >
          <RotateCcw aria-hidden="true" />
          Reset session
        </button>
      </div>
    </section>
  );
}
