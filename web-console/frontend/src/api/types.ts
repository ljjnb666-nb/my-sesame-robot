export type HealthResponse = {
  status: string;
  version: string;
  runtimeMode: string;
  simulatorOnly: boolean;
  provider: string;
};

export type RobotStateResponse = {
  runtimeMode: string;
  motionState: string | null;
  currentCommand: string | null;
  currentFace: string | null;
  emergencyStopActive: boolean | null;
  communicationTimedOut: boolean | null;
  batteryPercent: number | null;
  robotPose: string | null;
  chargingState: string | null;
  faults: string[];
};

export type TimelineEvent = {
  time?: string;
  timestamp?: string;
  eventType?: string;
  action?: string;
  result?: string | Record<string, unknown>;
  reason?: string;
  safetySeverity?: string;
  runtimeMode?: string;
  fault?: string;
};

export type TimelineResponse = {
  events: TimelineEvent[];
  limit: number;
};

export type ChatRequest = {
  text: string;
  confirmationId: string | null;
};

export type ChatResponse = {
  status: string;
  message?: string;
  userMessage?: string;
  action?: string | null;
  requiresConfirmation?: boolean;
  confirmationId?: string;
  confirmationFingerprint?: string | null;
  structured?: Record<string, unknown>;
  reason?: string | null;
};

export type FaultResponse = {
  status: string;
  fault: string;
  state: RobotStateResponse;
};

export type SimulatorResetResponse = {
  status: string;
  generation: number;
  state: RobotStateResponse;
};

export type SessionResetResponse = {
  status: string;
  sessionId: string;
  runtimeConfirmationsRevoked: boolean;
};

export type ApiErrorCode =
  | "abort"
  | "timeout"
  | "offline"
  | "invalid_json"
  | "invalid_response"
  | "unsafe_mode"
  | "api_error";

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status?: number;
  readonly detail?: string;

  constructor(code: ApiErrorCode, message: string, options: { status?: number; detail?: string } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = options.status;
    this.detail = options.detail;
  }
}
