import { useMemo } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmtMoney } from '../lib/format'

// Single-series value-over-time chart (portfolio or stock price).
// Per the dataviz specs: one axis, 2px line, recessive grid, crosshair +
// tooltip hover layer, no legend (the card title names the series). Polarity
// (up/down over the visible window) picks the color; the header next to the
// chart always carries the signed number, so color is never the only signal.

function readToken(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function formatTick(timestamp, period) {
  const date = new Date(timestamp)
  if (period === '1D') {
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  }
  if (period === '1W' || period === '1M') {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }
  return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
}

function ChartTooltip({ active, payload, period }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-sm">
      <div className="font-semibold text-ink">{fmtMoney(point.value)}</div>
      <div className="mt-0.5 text-ink-muted">
        {new Date(point.timestamp).toLocaleString('en-US', {
          month: 'short',
          day: 'numeric',
          ...(period === '1D' || period === '1W'
            ? { hour: 'numeric', minute: '2-digit' }
            : { year: 'numeric' }),
        })}
      </div>
    </div>
  )
}

export default function ValueChart({ points, period, height = 260 }) {
  // points: [{ timestamp, value }] in time order
  const { stroke, inkMuted, border } = useMemo(
    () => ({
      stroke:
        points.length > 1 && points[points.length - 1].value < points[0].value
          ? readToken('--t-down')
          : readToken('--t-up'),
      inkMuted: readToken('--t-ink-muted'),
      border: readToken('--t-border'),
    }),
    // re-read tokens when data or theme-sensitive render happens
    [points],
  )

  if (!points.length) {
    return (
      <div className="flex items-center justify-center text-sm text-ink-muted" style={{ height }}>
        No data yet for this period.
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
        <defs>
          <linearGradient id="valueFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity={0.18} />
            <stop offset="100%" stopColor={stroke} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={border} strokeDasharray="0" vertical={false} />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(t) => formatTick(t, period)}
          tick={{ fill: inkMuted, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          minTickGap={48}
        />
        <YAxis
          domain={['auto', 'auto']}
          tickFormatter={(v) => fmtMoney(v)}
          tick={{ fill: inkMuted, fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={80}
        />
        <Tooltip
          content={<ChartTooltip period={period} />}
          cursor={{ stroke: inkMuted, strokeDasharray: '3 3' }}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={stroke}
          strokeWidth={2}
          fill="url(#valueFill)"
          dot={false}
          activeDot={{ r: 4, strokeWidth: 2, stroke: 'var(--t-surface)' }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
