import { FormEvent, useState } from "react";
import { RotateCcw, Trash2, Zap } from "lucide-react";
import { faultLabel, t } from "../i18n/zh-CN";
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
    } catch {
      setError(t("controls.simulatorFailed"));
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
        <h2>{t("panel.controls")}</h2>
        <span>{t("panel.backendAllowlist")}</span>
      </div>
      <ErrorBanner message={error} tone="danger" />
      <form className="fault-form" onSubmit={submit}>
        <label htmlFor="fault-input">{t("controls.faultInjection")}</label>
        <div className="fault-row">
          <input
            id="fault-input"
            list="fault-suggestions"
            value={fault}
            maxLength={80}
            disabled={disabled || busy}
            onChange={(event) => setFault(event.target.value)}
            placeholder={t("controls.faultPlaceholder")}
          />
          <button type="submit" disabled={disabled || busy || !fault.trim()}>
            <Zap aria-hidden="true" />
            {t("button.inject")}
          </button>
        </div>
        <small className="form-help">{t("controls.suggestions")}</small>
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
            {t("controls.clearFault", { fault: faultLabel(item) })}
          </button>
        ))}
        <button type="button" className="secondary-button" disabled={disabled || busy} onClick={() => void run(onClearAll)}>
          <Trash2 aria-hidden="true" />
          {t("button.clearAllFaults")}
        </button>
      </div>
      <div className="reset-actions">
        <button
          type="button"
          className="danger-button"
          disabled={disabled || busy}
          onClick={() => {
            if (window.confirm(t("controls.resetSimulatorConfirm"))) {
              void run(onResetSimulator);
            }
          }}
        >
          <RotateCcw aria-hidden="true" />
          {t("button.resetSimulator")}
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={disabled || busy}
          onClick={() => {
            if (window.confirm(t("controls.resetSessionConfirm"))) {
              void run(onResetSession);
            }
          }}
        >
          <RotateCcw aria-hidden="true" />
          {t("button.resetSession")}
        </button>
      </div>
    </section>
  );
}
