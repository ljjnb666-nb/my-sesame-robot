import { apiClient } from "../api/client";
import { RobotStateResponse } from "../api/types";
import { usePolling } from "./usePolling";

export function useRobotState(enabled: boolean) {
  return usePolling<RobotStateResponse>(enabled, 1_500, (signal) => apiClient.state({ signal }));
}
