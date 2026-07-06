import { request } from './client'

export function getSummary() {
  return request('/portfolio/summary')
}

export function getPositions() {
  return request('/portfolio/positions')
}

export function getHistory(period = '1M') {
  return request(`/portfolio/history?period=${period}`)
}
