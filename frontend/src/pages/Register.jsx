import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/auth'
import { useAuth } from '../store/auth'
import { AuthShell, Field, FormError, SubmitButton } from './Login'

export default function Register() {
  const navigate = useNavigate()
  const setSession = useAuth((s) => s.setSession)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError(null)
    if (!/^\S+@\S+\.\S+$/.test(email)) return setError('Enter a valid email address.')
    if (password.length < 8) return setError('Password must be at least 8 characters.')
    if (password !== confirm) return setError('Passwords do not match.')

    setBusy(true)
    try {
      // register returns a token, so signup logs straight in
      const { access_token, email: registeredEmail } = await register(email, password)
      setSession(access_token, registeredEmail)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.status === 409 ? 'That email is already registered. Try logging in.' : err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell title="Create your account" subtitle="You start with $100,000 in paper cash.">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="new-password" placeholder="At least 8 characters" />
        <Field label="Confirm password" type="password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
        {error && <FormError message={error} />}
        <SubmitButton busy={busy}>Sign up</SubmitButton>
      </form>
      <p className="mt-6 text-center text-sm text-ink-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent-strong hover:underline">
          Log in
        </Link>
      </p>
    </AuthShell>
  )
}
