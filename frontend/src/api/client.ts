import type { MarketInfo, Opportunity, StatusResponse } from '../types'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    throw new Error(`Falha ao consultar ${path}: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

export function getMarkets(): Promise<MarketInfo[]> {
  return getJSON<MarketInfo[]>('/api/markets')
}

export function getOpportunities(market: string): Promise<Opportunity[]> {
  return getJSON<Opportunity[]>(`/api/markets/${market}/opportunities`)
}

export function getAssetHistory(market: string, ativo: string): Promise<Opportunity[]> {
  return getJSON<Opportunity[]>(`/api/markets/${market}/opportunities/${ativo}/history`)
}

export function getStatus(): Promise<StatusResponse> {
  return getJSON<StatusResponse>('/api/status')
}
