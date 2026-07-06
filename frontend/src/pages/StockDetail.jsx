import { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { listOrders } from '../api/orders'
import { getQuote, getStockHistory } from '../api/stocks'
import OrderForm from '../components/OrderForm'
import PeriodSelector from '../components/PeriodSelector'
import ValueChart from '../components/ValueChart'
import { fmtMoney, fmtSignedMoney, fmtSignedPct, plArrow, plClass } from '../lib/format'
import { OrderStatusBadge } from './Orders'

export default function StockDetail() {
  const { ticker: rawTicker } = useParams()
  const ticker = rawTicker.toUpperCase()

  const [quote, setQuote] = useState(null)
  const [quoteError, setQuoteError] = useState(null)
  const [period, setPeriod] = useState('1M')
  const [history, setHistory] = useState(null)
  const [orders, setOrders] = useState([])

  const refreshOrders = useCallback(() => {
    listOrders(ticker).then(setOrders).catch(() => setOrders([]))
  }, [ticker])

  useEffect(() => {
    setQuote(null)
    setQuoteError(null)
    getQuote(ticker).then(setQuote).catch((err) => setQuoteError(err.message))
    refreshOrders()
  }, [ticker, refreshOrders])

  useEffect(() => {
    setHistory(null)
    getStockHistory(ticker, period)
      .then(setHistory)
      .catch(() => setHistory({ points: [] }))
  }, [ticker, period])

  const chartPoints = useMemo(
    () =>
      (history?.points ?? []).map((point) => ({
        timestamp: point.timestamp,
        value: Number(point.close),
      })),
    [history],
  )

  if (quoteError) {
    return (
      <p className="text-sm text-ink-muted">
        Couldn&apos;t find <span className="font-semibold text-ink">{ticker}</span> — {quoteError}
      </p>
    )
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-6">
        <section>
          <h1 className="text-2xl font-semibold tracking-tight">{ticker}</h1>
          {quote ? (
            <>
              <p className="mt-1 text-3xl font-semibold">{fmtMoney(quote.price)}</p>
              {quote.change !== null && (
                <p className={`mt-1 text-sm font-medium ${plClass(quote.change)}`}>
                  {plArrow(quote.change)} {fmtSignedMoney(quote.change)} ({fmtSignedPct(quote.change_pct)}) today
                </p>
              )}
            </>
          ) : (
            <p className="mt-1 text-sm text-ink-muted">Loading quote…</p>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-surface p-4">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-ink-secondary">Price</h2>
            <PeriodSelector value={period} onChange={setPeriod} />
          </div>
          {history === null ? (
            <div className="flex h-[260px] items-center justify-center text-sm text-ink-muted">Loading chart…</div>
          ) : (
            <ValueChart points={chartPoints} period={period} />
          )}
        </section>

        <section className="rounded-2xl border border-border bg-surface">
          <h2 className="border-b border-border px-4 py-3 text-sm font-semibold text-ink-secondary">
            Your {ticker} orders
          </h2>
          {orders.length === 0 ? (
            <p className="px-4 py-6 text-center text-sm text-ink-muted">No orders for {ticker} yet.</p>
          ) : (
            <ul>
              {orders.slice(0, 8).map((order) => (
                <li key={order.id} className="flex items-center justify-between border-t border-border px-4 py-3 text-sm first:border-t-0">
                  <div>
                    <span className={`font-semibold ${order.side === 'BUY' ? 'text-up' : 'text-down'}`}>
                      {order.side}
                    </span>{' '}
                    {order.quantity} · {order.order_type.toLowerCase()}
                    {order.limit_price && ` @ ${fmtMoney(order.limit_price)}`}
                    {order.fill_price && ` · filled ${fmtMoney(order.fill_price)}`}
                  </div>
                  <div className="flex items-center gap-3">
                    <OrderStatusBadge status={order.status} />
                    <span className="text-xs text-ink-muted">
                      {new Date(order.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <aside className="lg:sticky lg:top-20 lg:self-start">
        <div className="rounded-2xl border border-border bg-surface p-4">
          <h2 className="mb-4 text-sm font-semibold text-ink-secondary">Trade {ticker}</h2>
          <OrderForm ticker={ticker} currentPrice={quote?.price} onPlaced={refreshOrders} />
        </div>
      </aside>
    </div>
  )
}
