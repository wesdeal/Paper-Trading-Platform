import { request } from './client'

export function getQuote(ticker) {
  return request(`/stocks/${encodeURIComponent(ticker)}/quote`)
}

export function getStockHistory(ticker, period = '1M') {
  return request(`/stocks/${encodeURIComponent(ticker)}/history?period=${period}`)
}
