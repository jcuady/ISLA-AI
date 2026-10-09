import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { IslaMark } from "@/components/isla-mark";

const SVG = resolve(__dirname, "../../public/isla-mark.svg");
const TSX = resolve(__dirname, "isla-mark.tsx");

function attributeIn(source: string, tag: string, name: string): string | null {
  const element = source.match(new RegExp(`<${tag}[^>]*>`))?.[0];
  return element?.match(new RegExp(`\\s${name}="([^"]*)"`))?.[1] ?? null;
}

describe("IslaMark", () => {
  it("renders an accessible image labelled as the brand mark", () => {
    const { container } = render(<IslaMark />);
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("role")).toBe("img");
    expect(svg.getAttribute("aria-label")).toBe("Isla AI mark");
  });

  it("defaults to 26px and honours an explicit size", () => {
    const { container: base } = render(<IslaMark />);
    expect(base.querySelector("svg")!.getAttribute("width")).toBe("26");

    const { container: big } = render(<IslaMark size={40} />);
    expect(big.querySelector("svg")!.getAttribute("height")).toBe("40");
  });

  it("inherits currentColor rather than hard-coding a fill", () => {
    // The same mark sits on the dark console and the light README. A hard-coded
    // fill here would mean two copies of the brand that can drift apart.
    const { container } = render(<IslaMark />);
    expect(container.querySelectorAll("path")).toHaveLength(1);
    expect(container.querySelector("path")!.getAttribute("fill")).toBe("currentColor");
    expect(container.querySelector("circle")!.getAttribute("stroke")).toBe("currentColor");
  });

  // The component inlines the geometry so it can inherit currentColor, which an
  // <img> cannot. That makes two copies by necessity - and a copy that silently
  // drifts from the generated master is how a brand ends up with two logos.
  it("keeps its inline geometry in sync with the generated SVG", () => {
    const svg = readFileSync(SVG, "utf8");
    const tsx = readFileSync(TSX, "utf8");
    expect(attributeIn(tsx, "path", "d")).toBe(attributeIn(svg, "path", "d"));
    expect(attributeIn(tsx, "circle", "r")).toBe(attributeIn(svg, "circle", "r"));
    // React spells the SVG attribute in camelCase in JSX; same value.
    expect(attributeIn(tsx, "circle", "strokeWidth")).toBe(
      attributeIn(svg, "circle", "stroke-width"),
    );
  });
});
