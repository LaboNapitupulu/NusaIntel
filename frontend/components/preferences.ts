// Storage is optional: blocked browser storage must not prevent analysis.
export function readPreference(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}

export function writePreference(key: string, value: string): void {
  try { window.localStorage.setItem(key, value); } catch { /* Keep the current session usable. */ }
}
