export interface MarketInfo {
  key: string
  label: string
}

export interface Opportunity {
  id: number
  market: string
  ativo: string
  referencia_operacional: string | null
  direcao: string
  horizonte: string
  confianca: number
  catalisador: string
  resumo: string
  riscos: string
  fontes: string[]
  panorama: string
  created_at: number
}

export interface StatusResponse {
  started_at: number
  uptime_seconds: number
  markets: Record<string, { last_updated_at: number | null }>
}

export interface Quote {
  symbol: string
  price: number | null
  change_pct: number | null
  volume: number | null
}

export interface ScanResult {
  ok: boolean
  total_oportunidades: number
  alertadas: number
  error: string | null
}
