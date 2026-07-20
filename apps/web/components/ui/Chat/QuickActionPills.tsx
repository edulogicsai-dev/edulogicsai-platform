'use client';

// FR4: sent as literal user messages -- NEXUS's existing free-text intent
// classification handles routing, no structured "intent" field exists on
// ChatRequest.
const QUICK_ACTIONS = ['Explain a concept', 'Practice question', 'Update my plan'];

interface QuickActionPillsProps {
  onSelect: (message: string) => void;
  disabled: boolean;
}

export default function QuickActionPills({ onSelect, disabled }: QuickActionPillsProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-2">
      {QUICK_ACTIONS.map((label) => (
        <button
          key={label}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(label)}
          className="px-3 py-1 text-sm rounded-full border border-zinc-600 text-zinc-200 hover:bg-zinc-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {label}
        </button>
      ))}
    </div>
  );
}
