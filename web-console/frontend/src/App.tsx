import { useCallback, useReducer, useState } from "react";
import { apiClient } from "./api/client";
import { ChatResponse } from "./api/types";
import { ApiStatus } from "./components/ApiStatus";
import { AppHeader } from "./components/AppHeader";
import { ChatPanel } from "./components/ChatPanel";
import { ConfirmationDialog } from "./components/ConfirmationDialog";
import { ErrorBanner } from "./components/ErrorBanner";
import { RobotOverview } from "./components/RobotOverview";
import { SimulatorControls } from "./components/SimulatorControls";
import { TimelinePanel } from "./components/TimelinePanel";
import { useApiHealth } from "./hooks/useApiHealth";
import { useRobotState } from "./hooks/useRobotState";
import { useTimeline } from "./hooks/useTimeline";
import { simulatorReducer } from "./state/simulatorReducer";
import { chatResponseText } from "./state/simulatorTypes";

const initialMessage = {
  id: "welcome",
  role: "system" as const,
  text: "Connected to local Sesame Robot Simulator. Real hardware is disabled.",
  createdAt: new Date(),
};

function message(role: "user" | "assistant" | "system", text: string) {
  return {
    id: crypto.randomUUID(),
    role,
    text,
    createdAt: new Date(),
  };
}

function confirmationState(response: ChatResponse): string | null {
  const runtime = response.structured?.runtime;
  if (typeof runtime !== "object" || runtime === null || !("confirmation" in runtime)) return null;
  const confirmation = runtime.confirmation;
  if (typeof confirmation !== "object" || confirmation === null || !("state" in confirmation)) return null;
  return String(confirmation.state);
}

export function App() {
  const { status, health, error: healthError, refresh: refreshHealth } = useApiHealth();
  const enabled = status === "online";
  const blocked = status === "blocked";
  const controlsDisabled = !enabled || blocked;
  const robot = useRobotState(enabled);
  const [timelineLimit, setTimelineLimit] = useState(20);
  const timeline = useTimeline(enabled, timelineLimit);
  const [chat, dispatch] = useReducer(simulatorReducer, { messages: [initialMessage], pendingConfirmation: null });
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);

  const refreshRuntime = useCallback(() => {
    void robot.refresh();
    void timeline.refresh();
  }, [robot, timeline]);

  const handleResponse = useCallback(
    (originalText: string, response: ChatResponse) => {
      dispatch({ type: "append", message: message("assistant", chatResponseText(response)) });
      if ((response.status === "confirmation_required" || response.requiresConfirmation) && response.confirmationId) {
        dispatch({
          type: "setConfirmation",
          confirmation: {
            originalText,
            confirmationId: response.confirmationId,
            action: response.action ?? "unknown_action",
            fingerprint: response.confirmationFingerprint ?? null,
            message: response.reason ?? response.message ?? "Robot action requires explicit browser confirmation.",
          },
        });
      }
      const result = confirmationState(response);
      if (result) {
        setBanner(`Confirmation result: ${result}`);
      }
      refreshRuntime();
    },
    [refreshRuntime],
  );

  const sendChat = useCallback(
    async (overrideText?: string) => {
      const text = (overrideText ?? input).trim();
      if (!text || text.length > 500 || controlsDisabled || sending) return;
      dispatch({ type: "append", message: message("user", text) });
      if (!overrideText) setInput("");
      setSending(true);
      setBanner(null);
      try {
        const response = await apiClient.chat({ text, confirmationId: null });
        handleResponse(text, response);
      } catch (caught) {
        if (!overrideText) setInput(text);
        dispatch({ type: "append", message: message("system", caught instanceof Error ? caught.message : "Chat request failed.") });
      } finally {
        setSending(false);
      }
    },
    [controlsDisabled, handleResponse, input, sending],
  );

  const confirmPending = useCallback(async () => {
    const pending = chat.pendingConfirmation;
    if (!pending || sending) return;
    setSending(true);
    setBanner(null);
    try {
      const response = await apiClient.chat({ text: pending.originalText, confirmationId: pending.confirmationId });
      dispatch({ type: "setConfirmation", confirmation: null });
      handleResponse(pending.originalText, response);
    } catch (caught) {
      dispatch({ type: "setConfirmation", confirmation: null });
      dispatch({ type: "append", message: message("system", caught instanceof Error ? caught.message : "Confirmation failed.") });
    } finally {
      setSending(false);
    }
  }, [chat.pendingConfirmation, handleResponse, sending]);

  const cancelPending = useCallback(() => {
    dispatch({ type: "setConfirmation", confirmation: null });
    setBanner("本次网页确认已取消，机器人动作未执行。");
  }, []);

  const resetSession = async () => {
    const response = await apiClient.resetSession();
    dispatch({ type: "clear" });
    dispatch({ type: "append", message: message("system", `Session reset. runtimeConfirmationsRevoked=${response.runtimeConfirmationsRevoked}`) });
    refreshRuntime();
  };

  const resetSimulator = async () => {
    await apiClient.resetSimulator();
    dispatch({ type: "setConfirmation", confirmation: null });
    refreshRuntime();
  };

  return (
    <div className="app-shell">
      <AppHeader status={status} health={health} error={healthError} onReconnect={() => void refreshHealth()} />
      <main>
        <ApiStatus status={status} error={healthError} />
        <ErrorBanner message={banner} />
        {robot.error && <ErrorBanner message={robot.error} />}
        <div className="dashboard-grid">
          <ChatPanel messages={chat.messages} input={input} disabled={controlsDisabled} sending={sending} onInput={setInput} onSend={(text) => void sendChat(text)} onClear={() => dispatch({ type: "clear" })} />
          <RobotOverview state={robot.data} lastUpdatedAt={robot.lastUpdatedAt} />
          <div className="right-column">
            <SimulatorControls
              disabled={controlsDisabled}
              faults={robot.data?.faults ?? []}
              onInject={async (fault) => {
                await apiClient.injectFault(fault);
                refreshRuntime();
              }}
              onClear={async (fault) => {
                await apiClient.clearFault(fault);
                refreshRuntime();
              }}
              onClearAll={async () => {
                await apiClient.clearFault("all");
                refreshRuntime();
              }}
              onResetSimulator={resetSimulator}
              onResetSession={resetSession}
            />
            <TimelinePanel timeline={timeline.data} limit={timelineLimit} loading={timeline.loading} error={timeline.error} onLimit={setTimelineLimit} onRefresh={() => void timeline.refresh()} />
          </div>
        </div>
      </main>
      <ConfirmationDialog confirmation={chat.pendingConfirmation} busy={sending} onConfirm={() => void confirmPending()} onCancel={cancelPending} />
    </div>
  );
}
