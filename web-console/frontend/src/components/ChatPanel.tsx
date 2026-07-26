import { useEffect, useRef } from "react";
import { t } from "../i18n/zh-CN";
import { ChatMessageModel } from "../state/simulatorTypes";
import { ChatComposer } from "./ChatComposer";
import { ChatMessage } from "./ChatMessage";
import { EmptyState } from "./EmptyState";
import { QuickCommands } from "./QuickCommands";

type Props = {
  messages: ChatMessageModel[];
  input: string;
  disabled: boolean;
  sending: boolean;
  onInput: (value: string) => void;
  onSend: (text?: string) => void;
  onClear: () => void;
};

export function ChatPanel({ messages, input, disabled, sending, onInput, onSend, onClear }: Props) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const shouldStick = useRef(true);

  useEffect(() => {
    if (!shouldStick.current || !listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  return (
    <section className="panel chat-panel">
      <div className="panel-title">
        <h2>{t("panel.chat")}</h2>
        <button type="button" className="secondary-button" onClick={onClear} disabled={disabled || sending}>
          {t("button.clearChat")}
        </button>
      </div>
      <div
        className="message-list"
        ref={listRef}
        onScroll={() => {
          if (!listRef.current) return;
          const distance = listRef.current.scrollHeight - listRef.current.scrollTop - listRef.current.clientHeight;
          shouldStick.current = distance < 48;
        }}
      >
        {messages.length ? messages.map((message) => <ChatMessage key={message.id} message={message} />) : <EmptyState title={t("chat.empty")} />}
      </div>
      <QuickCommands disabled={disabled || sending} onSend={(text) => onSend(text)} />
      <ChatComposer value={input} disabled={disabled} sending={sending} onChange={onInput} onSubmit={() => onSend()} />
    </section>
  );
}
