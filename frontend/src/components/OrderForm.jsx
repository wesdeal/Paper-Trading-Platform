import { useState } from 'react'
import { placeOrder } from '../api/orders'
import { fmtMoney } from '../lib/format'

function Toggle({ options, value, onChange, activeClass }) {
  return (
    <div className="grid grid-cols-2 gap-1 rounded-xl bg-surface-2 p-1">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`rounded-lg py-1.5 text-sm font-semibold capitalize transition-colors ${
            value === option ? activeClass : 'text-ink-muted hover:text-ink-secondary'
          }`}
        >
          {option.toLowerCase()}
        </button>
      ))}
    </div>
  )
}

export default function OrderForm({ ticker, currentPrice, onPlaced }) {
  const [side, setSide] = useState('BUY')
  const [orderType, setOrderType] = useState('MARKET')
  const [quantity, setQuantity] = useState('')
  const [limitPrice, setLimitPrice] = useState('')
  const [error, setError] = useState(null)
  const [confirmation, setConfirmation] = useState(null)
  const [busy, setBusy] = useState(false)

  const qty = parseInt(quantity, 10)
  const perShare = orderType === 'LIMIT' ? parseFloat(limitPrice) : Number(currentPrice)
  const estimated = qty > 0 && perShare > 0 ? qty * perShare : null

  const submit = async (event) => {
    event.preventDefault()
    setError(null)
    setConfirmation(null)
    if (!(qty > 0)) return setError('Enter a whole number of shares.')
    if (orderType === 'LIMIT' && !(parseFloat(limitPrice) > 0)) {
      return setError('Enter a limit price.')
    }

    setBusy(true)
    try {
      const order = await placeOrder({
        ticker,
        side,
        quantity: qty,
        orderType,
        limitPrice: orderType === 'LIMIT' ? parseFloat(limitPrice) : null,
      })
      setConfirmation(
        order.status === 'PENDING'
          ? `Limit ${side.toLowerCase()} placed — fills when ${ticker} ${side === 'BUY' ? '≤' : '≥'} ${fmtMoney(order.limit_price)}.`
          : `${side === 'BUY' ? 'Bought' : 'Sold'} ${order.quantity} ${ticker} at market.`,
      )
      setQuantity('')
      setLimitPrice('')
      onPlaced?.(order)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const inputClass =
    'w-full rounded-xl border border-border bg-bg px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-ink-muted focus:border-accent'

  return (
    <form onSubmit={submit} className="space-y-4">
      <Toggle
        options={['BUY', 'SELL']}
        value={side}
        onChange={setSide}
        activeClass={side === 'BUY' ? 'bg-surface text-up shadow-sm' : 'bg-surface text-down shadow-sm'}
      />
      <Toggle
        options={['MARKET', 'LIMIT']}
        value={orderType}
        onChange={setOrderType}
        activeClass="bg-surface text-ink shadow-sm"
      />

      <label className="block">
        <span className="mb-1 block text-sm font-medium text-ink-secondary">Shares</span>
        <input
          inputMode="numeric"
          value={quantity}
          onChange={(event) => setQuantity(event.target.value.replace(/\D/g, ''))}
          placeholder="0"
          className={inputClass}
        />
      </label>

      {orderType === 'LIMIT' && (
        <label className="block">
          <span className="mb-1 block text-sm font-medium text-ink-secondary">Limit price</span>
          <input
            inputMode="decimal"
            value={limitPrice}
            onChange={(event) => setLimitPrice(event.target.value.replace(/[^0-9.]/g, ''))}
            placeholder={currentPrice ? Number(currentPrice).toFixed(2) : '0.00'}
            className={inputClass}
          />
          <span className="mt-1 block text-xs text-ink-muted">
            Fills when the price {side === 'BUY' ? 'drops to or below' : 'rises to or above'} your limit.
          </span>
        </label>
      )}

      <div className="flex items-center justify-between border-t border-border pt-3 text-sm">
        <span className="text-ink-muted">Estimated {side === 'BUY' ? 'cost' : 'credit'}</span>
        <span className="font-semibold">{estimated !== null ? fmtMoney(estimated) : '—'}</span>
      </div>

      {error && (
        <p role="alert" className="rounded-xl bg-down/10 px-3.5 py-2.5 text-sm text-down">{error}</p>
      )}
      {confirmation && (
        <p className="rounded-xl bg-accent/10 px-3.5 py-2.5 text-sm text-accent-strong">{confirmation}</p>
      )}

      <button
        type="submit"
        disabled={busy}
        className={`w-full rounded-xl py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 ${
          side === 'BUY' ? 'bg-accent-strong' : 'bg-down'
        }`}
      >
        {busy ? 'Placing…' : `${side === 'BUY' ? 'Buy' : 'Sell'} ${ticker}`}
      </button>
    </form>
  )
}
