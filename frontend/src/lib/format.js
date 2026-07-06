const usd = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })

export function fmtMoney(value) {
  const n = Number(value)
  return Number.isFinite(n) ? usd.format(n) : '—'
}

// "+$123.45" / "−$67.89" -- the sign is the CVD-safe half of the green/red encoding
export function fmtSignedMoney(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return `${n < 0 ? '−' : '+'}${usd.format(Math.abs(n))}`
}

export function fmtSignedPct(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return `${n < 0 ? '−' : '+'}${Math.abs(n).toFixed(2)}%`
}

export function plClass(value) {
  return Number(value) < 0 ? 'text-down' : 'text-up'
}

export function plArrow(value) {
  return Number(value) < 0 ? '▾' : '▴'
}
