import { chatRoleLabel } from "../i18n/zh-CN";
import { ChatMessageModel } from "../state/simulatorTypes";

export function ChatMessage({ message }: { message: ChatMessageModel }) {
  return (
    <article className={`chat-message ${message.role}`}>
      <div>
        <strong>{chatRoleLabel(message.role)}</strong>
        <time>{message.createdAt.toLocaleTimeString()}</time>
      </div>
      <p>{message.text}</p>
    </article>
  );
}
