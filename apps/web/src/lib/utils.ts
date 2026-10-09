import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * shadcn's class merger: `clsx` handles conditionals, `twMerge` resolves
 * conflicting Tailwind utilities so a `className` prop reliably overrides
 * component defaults (last write wins rather than depending on CSS order).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}