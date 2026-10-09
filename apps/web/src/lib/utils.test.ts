import { describe, it, expect } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("drops falsy values so conditional classes are safe inline", () => {
    expect(cn("base", false && "never", null, undefined, "")).toBe("base");
  });

  it("lets a later class override an earlier conflicting utility", () => {
    // This is the whole reason tailwind-merge is here: a caller's `className`
    // must win over a component's default padding without `!important`.
    expect(cn("px-2 py-1", "px-6")).toBe("py-1 px-6");
  });

  it("keeps non-conflicting utilities in order", () => {
    expect(cn("rounded-md", "text-white")).toBe("rounded-md text-white");
  });

  it("accepts object and array forms via clsx", () => {
    expect(cn(["a", { b: true, c: false }])).toBe("a b");
  });
});