import type { MarketInfo } from '../types'

interface Props {
  markets: MarketInfo[]
  active: string
  onChange: (key: string) => void
}

export function MarketTabs({ markets, active, onChange }: Props) {
  return (
    <div className="flex gap-1 rounded-lg bg-white/5 p-1">
      {markets.map((m) => (
        <button
          key={m.key}
          type="button"
          onClick={() => onChange(m.key)}
          className={`rounded-md px-4 py-2 text-sm font-medium transition ${
            active === m.key
              ? 'bg-white/10 text-slate-100 shadow'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  )
}
