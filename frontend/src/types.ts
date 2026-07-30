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
