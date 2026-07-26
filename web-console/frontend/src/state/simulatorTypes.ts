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
