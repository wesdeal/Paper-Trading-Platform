const PERIODS = ['1D', '1W', '1M', '3M', 'ALL']

export default function PeriodSelector({ value, onChange }) {
  return (
    <div className="flex gap-1" role="tablist" aria-label="Chart period">
      {PERIODS.map((period) => (
        <button
          key={period}
          role="tab"
          aria-selected={value === period}
          onClick={() => onChange(period)}
          className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
            value === period
              ? 'bg-accent/15 text-accent-strong'
              : 'text-ink-muted hover:text-ink-secondary'
          }`}
        >
          {period}
        </button>
      ))}
    </div>
  )
}
