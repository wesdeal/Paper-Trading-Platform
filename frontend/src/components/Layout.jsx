import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../store/auth'

function useTheme() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const toggle = () => {
    const next = !dark
    document.documentElement.classList.toggle('dark', next)
    localStorage.setItem('theme', next ? 'dark' : 'light')
    setDark(next)
  }
  return { dark, toggle }
}

const navLinkClass = ({ isActive }) =>
  `rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive ? 'bg-surface-2 text-ink' : 'text-ink-secondary hover:text-ink'
  }`

export default function Layout() {
  const { email, logout } = useAuth()
  const { dark, toggle } = useTheme()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')

  const submitSearch = (event) => {
    event.preventDefault()
    const ticker = search.trim().toUpperCase()
    if (!ticker) return
    setSearch('')
    navigate(`/stocks/${ticker}`)
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <NavLink to="/dashboard" className="text-lg font-semibold tracking-tight text-accent-strong">
            papertrade
          </NavLink>

          <nav className="flex items-center gap-1">
            <NavLink to="/dashboard" className={navLinkClass}>Dashboard</NavLink>
            <NavLink to="/orders" className={navLinkClass}>Orders</NavLink>
          </nav>

          <form onSubmit={submitSearch} className="order-last w-full sm:order-none sm:ml-2 sm:w-auto sm:flex-1 sm:max-w-xs">
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search ticker (e.g. AAPL)"
              aria-label="Search ticker"
              className="w-full rounded-full border border-border bg-surface px-4 py-1.5 text-sm outline-none transition-colors placeholder:text-ink-muted focus:border-accent"
            />
          </form>

          <div className="ml-auto flex items-center gap-3">
            <button
              onClick={toggle}
              aria-label="Toggle dark mode"
              className="rounded-full px-2 py-1 text-sm text-ink-secondary transition-colors hover:text-ink"
            >
              {dark ? '☾' : '☀'}
            </button>
            <span className="hidden text-sm text-ink-muted md:inline">{email}</span>
            <button
              onClick={logout}
              className="rounded-full border border-border px-3 py-1.5 text-sm text-ink-secondary transition-colors hover:border-down hover:text-down"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
