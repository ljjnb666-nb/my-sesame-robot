import { FormEvent, KeyboardEvent } from "react";
import { Send } from "lucide-react";

const LIMIT = 500;

type Props = {
  value: string;
  disabled: boolean;
  sending: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function ChatComposer({ value, disabled, sending, onChange, onSubmit }: Props) {
  const remaining = LIMIT - value.length;
  const canSend = value.trim().length > 0 && value.length <= LIMIT && !disabled && !sending;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSend) onSubmit();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) onSubmit();
    }
  };

  return (
    <form className="chat-composer" onSubmit={submit}>
      <label htmlFor="chat-input">AI 指令</label>
      <textarea
        id="chat-input"
        value={value}
        maxLength={LIMIT}
        disabled={disabled || sending}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        rows={3}
        placeholder="输入高级动作或状态查询..."
      />
      <div className="composer-actions">
        <span className={remaining < 30 ? "warn-text" : ""}>剩余 {remaining}</span>
        <button type="submit" disabled={!canSend}>
          <Send aria-hidden="true" />
          Send
        </button>
      </div>
    </form>
  );
}
