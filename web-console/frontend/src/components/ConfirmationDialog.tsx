import { useEffect, useRef } from "react";
import { AlertTriangle } from "lucide-react";
import { PendingConfirmation } from "../state/simulatorTypes";

type Props = {
  confirmation: PendingConfirmation | null;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmationDialog({ confirmation, busy, onConfirm, onCancel }: Props) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const cancelRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!confirmation) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    cancelRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCancel();
      }
      if (event.key === "Enter") {
        event.preventDefault();
      }
      if (event.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>("button:not(:disabled), [tabindex='0']"));
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first || !last) return;
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      previous?.focus();
    };
  }, [confirmation, onCancel]);

  if (!confirmation) return null;

  return (
    <div className="dialog-backdrop">
      <div className="confirmation-dialog" role="dialog" aria-modal="true" aria-labelledby="confirmation-title" ref={dialogRef} tabIndex={-1}>
        <div className="dialog-title">
          <AlertTriangle aria-hidden="true" />
          <h2 id="confirmation-title">Confirm Robot Action</h2>
        </div>
        <dl>
          <dt>Action</dt>
          <dd>{confirmation.action}</dd>
          <dt>Original request</dt>
          <dd>{confirmation.originalText}</dd>
          <dt>Reason</dt>
          <dd>{confirmation.message}</dd>
          <dt>Fingerprint</dt>
          <dd>{confirmation.fingerprint ?? "not provided"}</dd>
        </dl>
        <p className="warning-box">确认后才会重新调用 Chat API 消费当前网页内存里的确认令牌。确认 ID 不会显示、记录或持久化。</p>
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onCancel} disabled={busy} ref={cancelRef}>
            Cancel
          </button>
          <button type="button" className="danger-button" onClick={onConfirm} disabled={busy}>
            Confirm Action
          </button>
        </div>
      </div>
    </div>
  );
}
