import { describe, expect, it, vi } from "vitest";
import { ApiError, planChunks, withRetry } from "@/lib/api";
import { fmtBytes, fmtTs, judgeLabel, scoreColor } from "@/lib/format";

describe("planChunks", () => {
  it("covers the file exactly with a short last chunk", () => {
    const p = planChunks(20, 8);
    expect(p).toEqual([[0, 0, 8], [1, 8, 16], [2, 16, 20]]);
  });
  it("handles exact multiples and a 2 GB file", () => {
    expect(planChunks(16, 8)).toHaveLength(2);
    expect(planChunks(2 * 1024 ** 3, 8 * 1024 ** 2)).toHaveLength(256);
  });
});

describe("withRetry", () => {
  it("retries transient failures then succeeds", async () => {
    const fn = vi.fn().mockRejectedValueOnce(new ApiError("x", 503)).mockResolvedValue("ok");
    await expect(withRetry(fn, 3, 1, async () => {})).resolves.toBe("ok");
    expect(fn).toHaveBeenCalledTimes(2);
  });
  it("does not retry client errors", async () => {
    const fn = vi.fn().mockRejectedValue(new ApiError("bad", 400));
    await expect(withRetry(fn, 3, 1, async () => {})).rejects.toThrow("bad");
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe("format", () => {
  it("timestamps", () => { expect(fmtTs(65)).toBe("01:05"); expect(fmtTs(3725)).toBe("1:02:05"); });
  it("bytes", () => { expect(fmtBytes(500)).toBe("500 B"); expect(fmtBytes(340 * 1024 ** 2)).toBe("340 MB"); });
  it("score colours", () => { expect(scoreColor(5)).toContain("emerald"); expect(scoreColor(1)).toContain("rose"); });
  it("judge labels", () => {
    expect(judgeLabel("local")).toBe("Local heuristic scorer");
    expect(judgeLabel("gemini:gemini-2.5-flash")).toBe("Gemini LLM judge (gemini-2.5-flash)");
  });
});
