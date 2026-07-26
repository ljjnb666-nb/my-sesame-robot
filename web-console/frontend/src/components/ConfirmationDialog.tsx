import { useEffect, useRef } from "react";
import { AlertTriangle, LoaderCircle } from "lucide-react";
import { PendingConfirmation } from "../state/simulatorTypes";

type ConfirmationMode = "idle" | "submitting";

type Props = {
  confirmation: PendingConfirmation | null;
  mode: ConfirmationMode;
  onConfirm: () => void;
  onCancel: () => void;
};

function focusDialog(dialog: HTMLDivElement | null) {
  dialog?.focus();
}

export function ConfirmationDialog({ confirmation, mode, onConfirm, onCancel }: Props) {
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const cancelRef = useRef<HTMLButtonElement | null>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const wasOpenRef = useRef(false);
  const submitting = mode === "submitting";

  useEffect(() => {
    const open = confirmation !== null;
    if (open && !wasOpenRef.current) {
      openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    }
    if (!open && wasOpenRef.current) {
      openerRef.current?.focus();
      openerRef.current = null;
    }
    wasOpenRef.current = open;
  }, [confirmation]);

  useEffect(() => {
    if (!confirmation) return;
    if (submitting) {
      focusDialog(dialogRef.current);
    } else {
      cancelRef.current?.focus();
    }
  }, [confirmation, submitting]);

  useEffect(() => {
    if (!confirmation) return;
    const keepFocusInside = () => {
      const dialog = dialogRef.current;
      if (!dialog || dialog.contains(document.activeElement)) return;
      if (submitting) {
        focusDialog(dialog);
      } else {
        cancelRef.current?.focus();
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        if (!submitting) onCancel();
        return;
      }
      if (event.key === "Enter" || (submitting && event.key === " ")) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      if (event.key === "Tab" && dialogRef.current) {
        const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>("button:not(:disabled), [tabindex='0']"));
        if (focusable.length === 0) {
          event.preventDefault();
          event.stopPropagation();
          focusDialog(dialogRef.current);
          return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!dialogRef.current.contains(document.activeElement)) {
          event.preventDefault();
          first.focus();
        } else if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("focusin", keepFocusInside, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("focusin", keepFocusInside, true);
    };
  }, [confirmation, onCancel, submitting]);

  if (!confirmation) return null;

  return (
    <div className="dialog-backdrop">
      <div className="confirmation-dialog" role="dialog" aria-modal="true" aria-labelledby="confirmation-title" ref={dialogRef} tabIndex={-1}>
        <div className="dialog-title">
          {submitting ? <LoaderCircle className="spin" aria-hidden="true" /> : <AlertTriangle aria-hidden="true" />}
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
        <p className="warning-box">
          {submitting
            ? "正在等待 Runtime 返回最终结果。请勿关闭页面或重复提交。"
            : "确认后才会重新调用 Chat API 消费当前网页内存里的确认令牌。确认 ID 不会显示、记录或持久化。"}
        </p>
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onCancel} disabled={submitting} ref={cancelRef}>
            Cancel
          </button>
          <button type="button" className="danger-button" onClick={onConfirm} disabled={submitting}>
            Confirm Action
          </button>
        </div>
      </div>
    </div>
  );
}
