import { ChatMessageModel, ChatState, PendingConfirmation } from "./simulatorTypes";

export type ChatAction =
  | { type: "append"; message: ChatMessageModel }
  | { type: "clear" }
  | { type: "setConfirmation"; confirmation: PendingConfirmation | null };

export function simulatorReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "append":
      return { ...state, messages: [...state.messages, action.message] };
    case "clear":
      return { messages: [], pendingConfirmation: null };
    case "setConfirmation":
      return { ...state, pendingConfirmation: action.confirmation };
  }
}
