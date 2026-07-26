import { apiClient } from "../api/client";
import { TimelineResponse } from "../api/types";
import { usePolling } from "./usePolling";

export function useTimeline(enabled: boolean, limit: number) {
  return usePolling<TimelineResponse>(enabled, 2_500, (signal) => apiClient.timeline(limit, { signal }));
}
