import { request } from './client'

export function listOrders(ticker) {
  const query = ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''
  return request(`/orders/${query}`)
}

export function placeOrder({ ticker, side, quantity, orderType, limitPrice }) {
  return request('/orders/', {
    method: 'POST',
    body: {
      ticker,
      side,
      quantity,
      order_type: orderType,
      limit_price: orderType === 'LIMIT' ? limitPrice : null,
      // one key per submit click: a retry of the same click can't double-fill
      idempotency_key: crypto.randomUUID(),
    },
  })
}

export function cancelOrder(orderId) {
  return request(`/orders/${orderId}`, { method: 'DELETE' })
}
