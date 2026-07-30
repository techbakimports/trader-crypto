export function signalLabel(direcao: string, confianca: number): string {
  const alta = direcao.toLowerCase() === 'alta'
  if (confianca < 6) return 'Baixa confiança — apenas monitorar'
  if (confianca >= 8) return alta ? 'Sinal forte de alta nas fontes' : 'Sinal forte de baixa/cautela nas fontes'
  return alta ? 'Ficar de olho — viés de alta' : 'Ficar de olho — viés de baixa'
}

export function signalTone(direcao: string, confianca: number): 'up' | 'down' | 'neutral' {
  if (confianca < 6) return 'neutral'
  return direcao.toLowerCase() === 'alta' ? 'up' : 'down'
}

export function formatTimestamp(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
