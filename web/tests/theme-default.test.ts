import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { THEME_SCRIPT } from "../components/theme";

function env(saved: string | null) {
  const cls = new Set(["light"]);
  const h = { style: {} as any, classList: { add: (c: string) => cls.add(c), remove: (c: string) => cls.delete(c), contains: (c: string) => cls.has(c) } };
  const ls = { getItem: () => saved };
  new Function("document", "localStorage", "matchMedia", THEME_SCRIPT)({ documentElement: h }, ls, () => ({ matches: true }));
  return { cls, h };
}
describe("theme defaults to light", () => {
  it("stays light with no saved preference even if OS prefers dark", () => {
    const { cls, h } = env(null);
    expect(cls.has("dark")).toBe(false);
    expect(h.style.colorScheme).toBeUndefined();
  });
  it("applies dark only when the user saved dark", () => {
    const { cls } = env("dark");
    expect(cls.has("dark")).toBe(true);
    expect(env("light").cls.has("dark")).toBe(false);
  });
  it("never consults prefers-color-scheme", () => {
    expect(THEME_SCRIPT).not.toMatch(/prefers-color-scheme/);
    for (const f of ["app/layout.tsx", "app/globals.css"])
      expect(readFileSync(f, "utf8")).not.toMatch(/prefers-color-scheme:\s*dark/);
  });
});
