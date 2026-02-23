import { vi } from "vitest";

// --- Shared mock state ---

export let mockPathname = "/";
export function setMockPathname(path: string) {
  mockPathname = path;
}
export function resetMockPathname() {
  mockPathname = "/";
}

export const mockSetTheme = vi.fn();
export let mockResolvedTheme = "light";
export function setMockResolvedTheme(theme: string) {
  mockResolvedTheme = theme;
}
export function resetMockResolvedTheme() {
  mockResolvedTheme = "light";
}

export const mockPush = vi.fn();
export const mockReplace = vi.fn();
export const mockBack = vi.fn();
export const mockPrefetch = vi.fn();
