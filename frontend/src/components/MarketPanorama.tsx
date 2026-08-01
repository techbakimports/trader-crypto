interface Props {
  panorama: string
  updatedAt: number
}

export function MarketPanorama({ panorama, updatedAt }: Props) {
  const updated = new Date(updatedAt * 1000).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  return (
    <div className="mb-6 rounded-xl border border-sky-500/20 bg-sky-500/[0.06] p-4">
      <p className="text-sm font-semibold uppercase tracking-wide text-sky-400">
        Panorama do mercado — atualizado às {updated}
      </p>
      <p className="mt-2 text-base text-slate-200">{panorama}</p>
    </div>
  )
}
