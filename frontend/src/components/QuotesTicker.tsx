import type { Quote } from '../types'

interface Props {
  quotes: Quote[]
  market: string
}

function formatPrice(price: number | null, market: string): string {
  if (price === null) return '—'
  return market === 'b3'
    ? `R$ ${price.toFixed(2)}`
    : price >= 1
      ? `$${price.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
      : `$${price.toFixed(4)}`
}

export function QuotesTicker({ quotes, market }: Props) {
  if (quotes.length === 0) return null

  return (
    <div className="mb-6 overflow-x-auto rounded-xl border border-white/10 bg-white/[0.03]">
      <div className="flex min-w-max divide-x divide-white/10">
        {quotes.map((q) => {
          const up = (q.change_pct ?? 0) >= 0
          return (
            <div key={q.symbol} className="flex flex-col gap-1 px-5 py-4">
              <span className="text-sm font-medium text-slate-400">{q.symbol}</span>
              <span className="text-lg font-semibold text-slate-100">
                {formatPrice(q.price, market)}
              </span>
              {q.change_pct !== null && (
                <span className={`text-sm ${up ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {up ? '▲' : '▼'} {Math.abs(q.change_pct).toFixed(2)}%
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
