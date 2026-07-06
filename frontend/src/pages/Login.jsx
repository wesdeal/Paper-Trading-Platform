import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { getMyAccount } from '../api/accounts'
import { useAuth } from '../store/auth'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const setSession = useAuth((s) => s.setSession)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError(null)
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError('Enter a valid email address.')
    if (!password) return setError('Enter your password.')

    setBusy(true)
    try {
      const { access_token } = await login(email, password)
      // token first so the /accounts/me call is authenticated
      setSession(access_token, email.trim().toLowerCase())
      await getMyAccount().catch(() => null)
      navigate(location.state?.from?.pathname ?? '/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Log in to your paper trading account.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="current-password" />
        {error && <FormError message={error} />}
        <SubmitButton busy={busy}>Log in</SubmitButton>
      </form>
      <p className="mt-6 text-center text-sm text-ink-muted">
        No account?{' '}
        <Link to="/register" className="font-medium text-accent-strong hover:underline">
          Sign up
        </Link>
      </p>
    </AuthShell>
  )
}

export function AuthShell({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="text-2xl font-semibold tracking-tight text-accent-strong">papertrade</div>
          <h1 className="mt-6 text-xl font-semibold">{title}</h1>
          <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-6">{children}</div>
      </div>
    </div>
  )
}

export function Field({ label, type, value, onChange, autoComplete, placeholder }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-ink-secondary">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        placeholder={placeholder}
        className="w-full rounded-xl border border-border bg-bg px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-ink-muted focus:border-accent"
      />
    </label>
  )
}

export function FormError({ message }) {
  return (
    <p role="alert" className="rounded-xl bg-down/10 px-3.5 py-2.5 text-sm text-down">
      {message}
    </p>
  )
}

export function SubmitButton({ busy, children }) {
  return (
    <button
      type="submit"
      disabled={busy}
      className="w-full rounded-xl bg-accent-strong py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
    >
      {busy ? 'One moment…' : children}
    </button>
  )
}
