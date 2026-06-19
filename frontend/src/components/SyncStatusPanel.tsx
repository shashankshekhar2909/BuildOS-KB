"use client";
import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, SyncStatus } from "@/lib/api";

const STAGE_META: Record<string, { label: string; icon: string; color: string }> = {
  idle:           { label: "Idle",              icon: "○", color: "text-subtle" },
  extracting:     { label: "Reading files",     icon: "◌", color: "text-accent" },
  queuing_okf:    { label: "Queuing OKF",       icon: "◌", color: "text-accent" },
  generating_okf: { label: "Generating OKF",   icon: "◌", color: "text-warning" },
  okf_done:       { label: "OKF done",          icon: "◉", color: "text-success" },
  embedding:      { label: "Embedding",         icon: "◌", color: "text-accent" },
  done:           { label: "Done",              icon: "●", color: "text-success" },
  error:          { label: "Error",             icon: "✕", color: "text-error" },
};

const ACTIVE_STAGES = new Set(["extracting", "queuing_okf", "generating_okf", "embedding"]);

interface SyncStatusPanelProps {
  slug: string;
  active: boolean;
  onDone?: () => void;
}

export function SyncStatusPanel({ slug, active, onDone }: SyncStatusPanelProps) {
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  const { data } = useQuery<SyncStatus>({
    queryKey: ["sync-status", slug],
    queryFn: () => api.getSyncStatus(slug),
    enabled: active,
    refetchInterval: (query) => {
      const stage = query.state.data?.stage;
      if (!stage || stage === "idle" || stage === "done" || stage === "error") return false;
      return 1500;
    },
  });

  useEffect(() => {
    if (data?.stage === "done" || data?.stage === "error") {
      onDoneRef.current?.();
    }
  }, [data?.stage]);

  if (!active && !data) return null;
  if (!data || data.stage === "idle") return null;

  const meta = STAGE_META[data.stage] ?? STAGE_META.idle;
  const isSpinning = ACTIVE_STAGES.has(data.stage);
  const elapsed = data.ts ? Math.round((Date.now() / 1000) - data.ts) : 0;

  return (
    <div className={`mt-3 border px-4 py-3 text-xs transition-all ${
      data.stage === "done"
        ? "border-success/30 bg-success/5"
        : data.stage === "error"
        ? "border-error/30 bg-error/5"
        : "border-accent/30 bg-accent/5"
    }`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`${meta.color} ${isSpinning ? "animate-pulse" : ""} text-sm leading-none`}>
          {meta.icon}
        </span>
        <span className={`font-semibold ${meta.color}`}>{meta.label}</span>
        {isSpinning && elapsed > 0 && (
          <span className="text-subtle ml-auto">{elapsed}s</span>
        )}
      </div>
      <p className="text-muted leading-relaxed m-0">{data.msg}</p>
    </div>
  );
}

// Dashboard version — shows all active syncs from /api/admin/sync-activity
export function GlobalSyncActivity({ active }: { active: boolean }) {
  const { data } = useQuery({
    queryKey: ["sync-activity"],
    queryFn: api.getSyncActivity,
    enabled: active,
    refetchInterval: active ? 2000 : false,
  });

  const items = (data?.activity ?? []).filter((s) => s.stage !== "idle");
  if (!active || items.length === 0) return null;

  return (
    <div className="mt-3 border border-accent/30 bg-accent/5 px-4 py-3 text-xs">
      <div className="text-[10px] font-bold text-accent uppercase tracking-widest mb-2">
        Sync activity
      </div>
      <div className="flex flex-col gap-1.5">
        {items.map((s, i) => {
          const meta = STAGE_META[s.stage] ?? STAGE_META.idle;
          const isSpinning = ACTIVE_STAGES.has(s.stage);
          return (
            <div key={i} className="flex items-center gap-2">
              <span className={`${meta.color} ${isSpinning ? "animate-pulse" : ""} text-sm leading-none shrink-0`}>
                {meta.icon}
              </span>
              <span className="font-medium text-text truncate">{s.project_name || s.project_slug}</span>
              <span className="text-subtle truncate ml-auto shrink-0">{s.msg}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
