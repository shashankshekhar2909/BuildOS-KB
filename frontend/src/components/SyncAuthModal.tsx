"use client";
import { useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";

interface SyncButtonProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onConfirm: () => any;
  children: (trigger: () => void, disabled: boolean, reason: string | null) => React.ReactNode;
}

export function SyncAuthModal({ onConfirm, children }: SyncButtonProps) {
  const { user, loading } = useAuth();

  const disabled = loading || !user;
  const reason = loading ? "Checking session…" : !user ? "Sign in to use this action" : null;

  const trigger = useCallback(() => {
    if (!user) return;
    onConfirm();
  }, [user, onConfirm]);

  return <>{children(trigger, disabled, reason)}</>;
}
