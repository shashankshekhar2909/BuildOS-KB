"use client";
import { useState, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface SyncAuthModalProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onConfirm: () => any;
  children: (trigger: () => void) => React.ReactNode;
}

export function SyncAuthModal({ onConfirm, children }: SyncAuthModalProps) {
  const { user, login } = useAuth();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trigger = useCallback(() => {
    if (user) {
      onConfirm();
    } else {
      setOpen(true);
      setError(null);
    }
  }, [user, onConfirm]);

  const handleLogin = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await login();
      setOpen(false);
      await onConfirm();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }, [login, onConfirm]);

  return (
    <>
      {children(trigger)}

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
        >
          <div className="bg-surface border border-border w-full max-w-sm mx-4 p-6">
            <h2 className="text-base font-bold text-text mt-0 mb-1">Sign in to sync</h2>
            <p className="text-sm text-muted mb-5">
              Re-indexing runs LLM calls and uses API tokens. Sign in to confirm you&apos;re authorized.
            </p>

            {error && (
              <div className="mb-4 text-xs text-error bg-error/10 border border-error/20 px-3 py-2">
                {error}
              </div>
            )}

            <button
              onClick={handleLogin}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-border bg-surface-2 text-text text-sm font-semibold cursor-pointer hover:bg-surface transition-colors disabled:opacity-50"
            >
              <GoogleIcon />
              {loading ? "Signing in…" : "Sign in with Google"}
            </button>

            <button
              onClick={() => setOpen(false)}
              className="mt-3 w-full py-2 text-xs text-muted bg-transparent border-0 cursor-pointer hover:text-text transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  );
}
