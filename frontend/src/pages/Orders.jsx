import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { cancelOrder, listOrders } from '../api/orders'
import { fmtMoney } from '../lib/format'

const STATUS_STYLES = {
  FILLED: 'bg-accent/15 text-accent-strong',
  PENDING: 'bg-surface-2 text-ink-secondary',
  CANCELED: 'bg-surface-2 text-ink-muted line-through',
  REJECTED: 'bg-down/10 text-down',
}

export function OrderStatusBadge({ status }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[status] ?? 'bg-surface-2 text-ink-muted'}`}>
      {status.toLowerCase()}
    </span>
  )
}

export default function Orders() {
  const [orders, setOrders] = useState(null)
  const [error, setError] = useState(null)
  const [cancelingId, setCancelingId] = useState(null)

  useEffect(() => {
    listOrders().then(setOrders).catch((err) => setError(err.message))
  }, [])

  const handleCancel = async (orderId) => {
    setCancelingId(orderId)
    setError(null)
    try {
      const canceled = await cancelOrder(orderId)
      setOrders((current) => current.map((o) => (o.id === orderId ? canceled : o)))
    } catch (err) {
      setError(err.message)
    } finally {
      setCancelingId(null)
    }
  }

  if (error && !orders) return <p className="text-sm text-down">{error}</p>
  if (!orders) return <p className="text-sm text-ink-muted">Loading orders…</p>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold tracking-tight">Orders</h1>
      {error && <p className="text-sm text-down">{error}</p>}

      {orders.length === 0 ? (
        <p className="rounded-2xl border border-border bg-surface px-4 py-8 text-center text-sm text-ink-muted">
          No orders yet — search a ticker to place one.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-border bg-surface">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-muted">
                <th className="px-4 py-3 font-medium">Ticker</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Side</th>
                <th className="px-4 py-3 text-right font-medium">Qty</th>
                <th className="px-4 py-3 text-right font-medium">Limit</th>
                <th className="px-4 py-3 text-right font-medium">Fill</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Placed</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className="border-t border-border transition-colors hover:bg-surface-2/60">
                  <td className="px-4 py-3">
                    <Link to={`/stocks/${order.ticker}`} className="font-semibold text-accent-strong hover:underline">
                      {order.ticker}
                    </Link>
                  </td>
                  <td className="px-4 py-3 capitalize">{order.order_type.toLowerCase()}</td>
                  <td className={`px-4 py-3 font-medium ${order.side === 'BUY' ? 'text-up' : 'text-down'}`}>
                    {order.side}
                  </td>
                  <td className="px-4 py-3 text-right">{order.quantity}</td>
                  <td className="px-4 py-3 text-right">{order.limit_price ? fmtMoney(order.limit_price) : '—'}</td>
                  <td className="px-4 py-3 text-right">{order.fill_price ? fmtMoney(order.fill_price) : '—'}</td>
                  <td className="px-4 py-3"><OrderStatusBadge status={order.status} /></td>
                  <td className="px-4 py-3 text-ink-muted">
                    {new Date(order.created_at).toLocaleString('en-US', {
                      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
                    })}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {order.status === 'PENDING' && (
                      <button
                        onClick={() => handleCancel(order.id)}
                        disabled={cancelingId === order.id}
                        className="rounded-full border border-border px-3 py-1 text-xs font-medium text-ink-secondary transition-colors hover:border-down hover:text-down disabled:opacity-50"
                      >
                        {cancelingId === order.id ? 'Canceling…' : 'Cancel'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
