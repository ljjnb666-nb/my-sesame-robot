import { useEffect, useRef } from "react";
import { AlertTriangle, LoaderCircle } from "lucide-react";
import { actionLabel, t } from "../i18n/zh-CN";
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
          <h2 id="confirmation-title">{t("confirmation.title")}</h2>
        </div>
        <dl>
          <dt>{t("confirmation.action")}</dt>
          <dd>{actionLabel(confirmation.action)}</dd>
          <dt>{t("confirmation.originalRequest")}</dt>
          <dd>{confirmation.originalText}</dd>
          <dt>{t("confirmation.reason")}</dt>
          <dd>{confirmation.message}</dd>
          <dt>{t("confirmation.fingerprint")}</dt>
          <dd>{confirmation.fingerprint ?? t("confirmation.fingerprintMissing")}</dd>
        </dl>
        <p className="warning-box">{submitting ? t("confirmation.submitting") : t("confirmation.help")}</p>
        <div className="dialog-actions">
          <button type="button" className="secondary-button" onClick={onCancel} disabled={submitting} ref={cancelRef}>
            {t("button.cancel")}
          </button>
          <button type="button" className="danger-button" onClick={onConfirm} disabled={submitting}>
            {t("button.confirmAction")}
          </button>
        </div>
      </div>
    </div>
  );
}
