import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TimelineEvent } from "./TimelineEvent";

describe("TimelineEvent", () => {
  it("renders allowed result fields", () => {
    render(<TimelineEvent event={{ eventType: "fault", action: "inject", resultStatus: "ok", runtimeMode: "simulator" }} />);
    expect(screen.getByText("结果：已执行")).toBeInTheDocument();
    expect(screen.getByText(/代码：ok/)).toBeInTheDocument();
  });

  it("renders result state", () => {
    render(<TimelineEvent event={{ resultState: "accepted" }} />);
    expect(screen.getAllByText(/已确认并执行/).length).toBeGreaterThan(0);
  });

  it("renders result code", () => {
    render(<TimelineEvent event={{ resultCode: "stale_confirmation" }} />);
    expect(screen.getAllByText(/stale_confirmation/).length).toBeGreaterThan(0);
  });

  it("does not render confirmation id from unknown fields", () => {
    render(<TimelineEvent event={{ eventType: "x", resultStatus: "ok" }} />);
    expect(screen.queryByText(/[a-f0-9]{32}/i)).toBeNull();
  });

  it("uses generic result when no allowlisted field exists", () => {
    render(<TimelineEvent event={{ eventType: "x" }} />);
    expect(screen.getAllByText(/已有结果/).length).toBeGreaterThan(0);
  });
});
