import { useEffect, useState } from 'react'
import { getMarkets, getOpportunities } from './api/client'
import { AssetCard } from './components/AssetCard'
import { ComplianceFooter } from './components/ComplianceFooter'
import { MarketPanorama } from './components/MarketPanorama'
import { MarketTabs } from './components/MarketTabs'
import type { MarketInfo, Opportunity } from './types'

const POLL_INTERVAL_MS = 60_000

function App() {
  const [markets, setMarkets] = useState<MarketInfo[]>([])
  const [active, setActive] = useState<string>('')
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getMarkets()
      .then((data) => {
        setMarkets(data)
        if (data.length > 0) setActive(data[0].key)
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(() => {
    if (!active) return

    let cancelled = false

    function load() {
      getOpportunities(active)
        .then((data) => {
          if (!cancelled) {
            setOpportunities(data)
            setError(null)
          }
        })
        .catch((err: Error) => !cancelled && setError(err.message))
        .finally(() => !cancelled && setLoading(false))
    }

    setLoading(true)
    load()
    const id = setInterval(load, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [active])

  const sorted = [...opportunities].sort((a, b) => b.confianca - a.confianca)
  const latest = opportunities.reduce<Opportunity | null>(
    (acc, o) => (!acc || o.created_at > acc.created_at ? o : acc),
    null,
  )

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-6 py-8">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-100">Radar de Mercado</h1>
        <p className="mt-1 text-sm text-slate-400">
          Síntese diária de notícias, relatórios e ratings públicos por ativo.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          Não foi possível carregar os dados da API ({error}). Verifique se o backend
          (<code>server.py</code>) está rodando e acessível.
        </div>
      )}

      {markets.length > 0 && (
        <div className="mb-6">
          <MarketTabs markets={markets} active={active} onChange={setActive} />
        </div>
      )}

      {loading && <p className="text-sm text-slate-500">Carregando análises...</p>}

      {!loading && latest?.panorama && (
        <MarketPanorama panorama={latest.panorama} updatedAt={latest.created_at} />
      )}

      {!loading && sorted.length === 0 && !error && (
        <p className="text-sm text-slate-500">
          Nenhuma oportunidade registrada ainda para este mercado. O radar roda em ciclos
          periódicos — volte em instantes.
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sorted.map((opp) => (
          <AssetCard key={opp.id} opp={opp} />
        ))}
      </div>

      <ComplianceFooter />
    </div>
  )
}

export default App
