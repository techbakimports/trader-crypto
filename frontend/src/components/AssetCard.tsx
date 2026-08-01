import type { Opportunity } from '../types'
import { ConfidenceBadge } from './ConfidenceBadge'
import { formatTimestamp, signalLabel, signalTone } from '../lib/signal'

interface Props {
  opp: Opportunity
}

const TONE_STYLES: Record<'up' | 'down' | 'neutral', string> = {
  up: 'text-emerald-400',
  down: 'text-rose-400',
  neutral: 'text-slate-400',
}

export function AssetCard({ opp }: Props) {
  const tone = signalTone(opp.direcao, opp.confianca)
  const arrow = tone === 'up' ? '▲' : tone === 'down' ? '▼' : '•'

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-5 shadow-lg shadow-black/20 transition hover:border-white/20">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-2xl font-semibold ${TONE_STYLES[tone]}`}>{arrow}</span>
            <h3 className="text-xl font-semibold text-slate-100">{opp.ativo}</h3>
          </div>
          <p className={`mt-1 text-base font-medium ${TONE_STYLES[tone]}`}>
            {signalLabel(opp.direcao, opp.confianca)}
          </p>
        </div>
        <ConfidenceBadge confianca={opp.confianca} />
      </div>

      <dl className="grid grid-cols-2 gap-2 text-sm text-slate-400">
        <div>
          <dt className="uppercase tracking-wide text-slate-500">Horizonte</dt>
          <dd className="text-base text-slate-300">{opp.horizonte}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide text-slate-500">Atualizado em</dt>
          <dd className="text-base text-slate-300">{formatTimestamp(opp.created_at)}</dd>
        </div>
      </dl>

      <div className="space-y-3 text-base">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Catalisador
          </p>
          <p className="text-slate-200">{opp.catalisador}</p>
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Tese (síntese de fontes públicas)
          </p>
          <p className="text-slate-200">{opp.resumo}</p>
        </div>
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Riscos</p>
          <p className="text-slate-200">{opp.riscos}</p>
        </div>
      </div>

      {opp.fontes.length > 0 && (
        <div className="flex flex-wrap gap-1.5 border-t border-white/10 pt-3">
          {opp.fontes.map((fonte, i) => (
            <a
              key={i}
              href={fonte.startsWith('http') ? fonte : undefined}
              target="_blank"
              rel="noreferrer"
              className="max-w-full truncate rounded-full bg-white/5 px-3 py-1.5 text-sm text-sky-400 ring-1 ring-inset ring-white/10 hover:bg-white/10"
              title={fonte}
            >
              {fonte}
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
