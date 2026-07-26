import { ChatResponse } from "../api/types";

export type ChatRole = "user" | "assistant" | "system";

export type ChatMessageModel = {
  id: string;
  role: ChatRole;
  text: string;
  createdAt: Date;
};

export type PendingConfirmation = {
  originalText: string;
  confirmationId: string;
  action: string;
  fingerprint: string | null;
  message: string;
};

export type ChatState = {
  messages: ChatMessageModel[];
  pendingConfirmation: PendingConfirmation | null;
};

export function chatResponseText(response: ChatResponse): string {
  const confirmationState = response.structured?.runtime;
  const runtime = typeof confirmationState === "object" && confirmationState !== null ? confirmationState : null;
  const runtimeConfirmation = runtime && "confirmation" in runtime ? runtime.confirmation : null;
  const state =
    typeof runtimeConfirmation === "object" && runtimeConfirmation !== null && "state" in runtimeConfirmation
      ? String(runtimeConfirmation.state)
      : null;
  if (state) return `Confirmation result: ${state}`;
  if (response.message) return response.message;
  if (response.userMessage) return response.userMessage;
  if (response.status === "confirmation_required") return "此动作需要网页确认。";
  return response.status;
}
