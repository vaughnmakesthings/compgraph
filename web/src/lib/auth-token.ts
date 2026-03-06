let currentToken: string | null = null;
let authReady = false;
let authReadyResolve: (() => void) | null = null;
let authReadyPromise = createAuthPromise();

function createAuthPromise(): Promise<void> {
  return new Promise<void>((resolve) => {
    authReadyResolve = resolve;
  });
}

export function setAuthToken(token: string | null): void {
  currentToken = token;
  if (!authReady) {
    authReady = true;
    authReadyResolve?.();
  }
}

export function getAuthToken(): string | null {
  return currentToken;
}

export function isAuthReady(): boolean {
  return authReady;
}

export function waitForAuth(): Promise<void> {
  return authReadyPromise;
}

export function resetAuthState(): void {
  currentToken = null;
  authReady = false;
  authReadyPromise = createAuthPromise();
}
