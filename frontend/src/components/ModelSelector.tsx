"use client";
import { useQuery } from "@tanstack/react-query";
import { api, ModelOption } from "@/lib/api";

interface ModelSelectorProps {
  value: string;
  onChange: (model: string) => void;
  className?: string;
}

const PROVIDER_COLORS: Record<string, string> = {
  Groq: "#f97316",
  Gemini: "#4285f4",
  OpenAI: "#10a37f",
  Anthropic: "#d97706",
};

export function ModelSelector({ value, onChange, className = "" }: ModelSelectorProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["available-models"],
    queryFn: api.getAvailableModels,
    staleTime: 60_000,
  });

  if (isLoading || !data?.models.length) return null;

  const selected = data.models.find((m) => m.id === value) ?? data.models[0];

  return (
    <div className={`relative ${className}`}>
      <select
        value={value || data.default}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none bg-surface border border-border text-xs text-muted pl-3 pr-7 py-1.5 outline-none focus:border-accent cursor-pointer hover:border-border-2 transition-colors"
        title="Select LLM model for OKF generation"
      >
        {groupByProvider(data.models).map(({ provider, models }) => (
          <optgroup key={provider} label={provider}>
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>

      {/* Provider color dot */}
      <span
        className="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full pointer-events-none hidden"
        style={{ backgroundColor: PROVIDER_COLORS[selected?.provider ?? ""] ?? "#6f6f6f" }}
      />

      {/* Chevron */}
      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-subtle pointer-events-none text-[10px]">▾</span>
    </div>
  );
}

function groupByProvider(models: ModelOption[]) {
  const map: Record<string, ModelOption[]> = {};
  for (const m of models) {
    if (!map[m.provider]) map[m.provider] = [];
    map[m.provider].push(m);
  }
  return Object.entries(map).map(([provider, models]) => ({ provider, models }));
}
