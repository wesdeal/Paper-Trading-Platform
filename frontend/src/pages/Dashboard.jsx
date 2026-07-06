import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHistory, getPositions, getSummary } from '../api/portfolio'
import PeriodSelector from '../components/PeriodSelector'
import ValueChart from '../components/ValueChart'
import { usePortfolioSocket } from '../hooks/usePortfolioSocket'
import { fmtMoney, fmtSignedMoney, fmtSignedPct, plArrow, plClass } from '../lib/format'

export default function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [positions, setPositions] = useState([])
  const [period, setPeriod] = useState('1M')
  const [history, setHistory] = useState(null)
  const [error, setError] = useState(null)
  const { update, connected } = usePortfolioSocket()

  useEffect(() => {
    Promise.all([getSummary(), getPositions()])
      .then(([s, p]) => {
        setSummary(s)
        setPositions(p)
      })
      .catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    getHistory(period)
      .then(setHistory)
      .catch((err) => setError(err.message))
  }, [period])

  // websocket pushes supersede the REST snapshot as they arrive
  useEffect(() => {
    if (!update) return
    setSummary({
      cash_balance: update.cash_balance,
      positions_value: update.positions_value,
      total_value: update.total_value,
      total_gain_loss: update.total_gain_loss,
      total_gain_loss_pct: update.total_gain_loss_pct,
    })
    setPositions(update.positions)
  }, [update])

  const chartPoints = useMemo(
    () =>
      (history?.points ?? []).map((point) => ({
        timestamp: point.timestamp,
        value: Number(point.total_value),
      })),
    [history],
  )

  if (error) return <p className="text-sm text-down">{error}</p>
  if (!summary) return <p className="text-sm text-ink-muted">Loading portfolio…</p>

  const gain = Number(summary.total_gain_loss)

  return (
    <div className="space-y-6">
      <section>
        <div className="flex items-baseline gap-3">
          <h1 className="text-4xl font-semibold tracking-tight">{fmtMoney(summary.total_value)}</h1>
          {connected && (
            <span className="flex items-center gap-1.5 text-xs text-ink-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
              live
            </span>
          )}
        </div>
        <p className={`mt-1 text-sm font-medium ${plClass(gain)}`}>
          {plArrow(gain)} {fmtSignedMoney(gain)} ({fmtSignedPct(summary.total_gain_loss_pct)}) all time
        </p>
        <p className="mt-1 text-sm text-ink-muted">
          {fmtMoney(summary.cash_balance)} cash · {fmtMoney(summary.positions_value)} invested
        </p>
      </section>

      <section className="rounded-2xl border border-border bg-surface p-4">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink-secondary">Portfolio value</h2>
          <PeriodSelector value={period} onChange={setPeriod} />
        </div>
        {history === null ? (
          <div className="flex h-[260px] items-center justify-center text-sm text-ink-muted">Loading chart…</div>
        ) : (
          <ValueChart points={chartPoints} period={period} />
        )}
      </section>

      <section className="rounded-2xl border border-border bg-surface">
        <h2 className="border-b border-border px-4 py-3 text-sm font-semibold text-ink-secondary">Holdings</h2>
        {positions.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-ink-muted">
            No holdings yet — search a ticker above to place your first trade.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-ink-muted">
                  <th className="px-4 py-2 font-medium">Ticker</th>
                  <th className="px-4 py-2 text-right font-medium">Shares</th>
                  <th className="px-4 py-2 text-right font-medium">Avg cost</th>
                  <th className="px-4 py-2 text-right font-medium">Price</th>
                  <th className="px-4 py-2 text-right font-medium">Value</th>
                  <th className="px-4 py-2 text-right font-medium">Unrealized P&L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((position) => {
                  const pl = Number(position.unrealized_pl)
                  return (
                    <tr key={position.ticker} className="border-t border-border transition-colors hover:bg-surface-2/60">
                      <td className="px-4 py-3">
                        <Link to={`/stocks/${position.ticker}`} className="font-semibold text-accent-strong hover:underline">
                          {position.ticker}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right">{position.quantity}</td>
                      <td className="px-4 py-3 text-right">{fmtMoney(position.avg_cost_basis)}</td>
                      <td className="px-4 py-3 text-right">{fmtMoney(position.current_price)}</td>
                      <td className="px-4 py-3 text-right">{fmtMoney(position.current_value)}</td>
                      <td className={`px-4 py-3 text-right font-medium ${plClass(pl)}`}>
                        {plArrow(pl)} {fmtSignedMoney(pl)} ({fmtSignedPct(position.unrealized_pl_pct)})
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
