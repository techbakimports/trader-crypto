interface Props {
  confianca: number
}

export function ConfidenceBadge({ confianca }: Props) {
  const tone =
    confianca >= 8
      ? 'bg-emerald-500/15 text-emerald-400 ring-emerald-500/30'
      : confianca >= 6
        ? 'bg-amber-500/15 text-amber-400 ring-amber-500/30'
        : 'bg-slate-500/15 text-slate-400 ring-slate-500/30'

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium ring-1 ring-inset ${tone}`}
    >
      Confiança {confianca}/10
    </span>
  )
}
