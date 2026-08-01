import { useCallback, useEffect, useState } from 'react'
import { getMarkets, getOpportunities, getQuotes, triggerScan } from './api/client'
import { AssetCard } from './components/AssetCard'
import { ComplianceFooter } from './components/ComplianceFooter'
import { MarketPanorama } from './components/MarketPanorama'
import { MarketTabs } from './components/MarketTabs'
import { QuotesTicker } from './components/QuotesTicker'
import type { MarketInfo, Opportunity, Quote } from './types'

const POLL_INTERVAL_MS = 60_000
const QUOTES_POLL_INTERVAL_MS = 30_000

function App() {
  const [markets, setMarkets] = useState<MarketInfo[]>([])
  const [active, setActive] = useState<string>('')
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [quotes, setQuotes] = useState<Quote[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanMessage, setScanMessage] = useState<string | null>(null)

  useEffect(() => {
    getMarkets()
      .then((data) => {
        setMarkets(data)
        if (data.length > 0) setActive(data[0].key)
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  const loadOpportunities = useCallback((market: string) => {
    return getOpportunities(market).then((data) => {
      setOpportunities(data)
      setError(null)
    })
  }, [])

  useEffect(() => {
    if (!active) return

    let cancelled = false

    setLoading(true)
    loadOpportunities(active)
      .catch((err: Error) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false))

    const id = setInterval(() => {
      loadOpportunities(active).catch((err: Error) => !cancelled && setError(err.message))
    }, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [active, loadOpportunities])

  useEffect(() => {
    if (!active) return

    let cancelled = false

    function loadQuotes() {
      getQuotes(active)
        .then((data) => !cancelled && setQuotes(data))
        .catch(() => {
          /* cotação ao vivo é um extra — falha aqui não deve travar o resto da tela */
        })
    }

    loadQuotes()
    const id = setInterval(loadQuotes, QUOTES_POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [active])

  async function handleScan() {
    if (!active || scanning) return
    setScanning(true)
    setScanMessage(null)
    try {
      const result = await triggerScan(active)
      setScanMessage(
        result.ok
          ? `Ciclo concluído: ${result.total_oportunidades} oportunidade(s) encontrada(s)${
              result.error ? ` (aviso: ${result.error})` : ''
            }.`
          : `Ciclo falhou: ${result.error ?? 'erro desconhecido'}.`,
      )
      await loadOpportunities(active)
    } catch (err) {
      setScanMessage(`Falha ao disparar o ciclo: ${(err as Error).message}`)
    } finally {
      setScanning(false)
    }
  }

  const sorted = [...opportunities].sort((a, b) => b.confianca - a.confianca)
  const latest = opportunities.reduce<Opportunity | null>(
    (acc, o) => (!acc || o.created_at > acc.created_at ? o : acc),
    null,
  )

  return (
    <div className="mx-auto min-h-screen max-w-6xl px-6 py-8">
      <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">Radar de Mercado</h1>
          <p className="mt-1 text-sm text-slate-400">
            Síntese diária de notícias, relatórios e ratings públicos por ativo.
          </p>
        </div>
        <button
          type="button"
          onClick={handleScan}
          disabled={!active || scanning}
          className="rounded-lg bg-sky-500/15 px-4 py-2 text-sm font-medium text-sky-400 ring-1 ring-inset ring-sky-500/30 transition hover:bg-sky-500/25 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {scanning ? 'Analisando…' : 'Atualizar agora'}
        </button>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
          Não foi possível carregar os dados da API ({error}). Verifique se o backend
          (<code>server.py</code>) está rodando e acessível.
        </div>
      )}

      {scanMessage && (
        <div className="mb-6 rounded-lg border border-sky-500/20 bg-sky-500/5 px-4 py-3 text-sm text-sky-300">
          {scanMessage}
        </div>
      )}

      {markets.length > 0 && (
        <div className="mb-6">
          <MarketTabs markets={markets} active={active} onChange={setActive} />
        </div>
      )}

      <QuotesTicker quotes={quotes} market={active} />

      {loading && <p className="text-sm text-slate-500">Carregando análises...</p>}

      {!loading && latest?.panorama && (
        <MarketPanorama panorama={latest.panorama} updatedAt={latest.created_at} />
      )}

      {!loading && sorted.length === 0 && !error && (
        <p className="text-sm text-slate-500">
          Nenhuma oportunidade registrada ainda para este mercado. Clique em "Atualizar agora"
          ou aguarde o próximo ciclo automático.
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
