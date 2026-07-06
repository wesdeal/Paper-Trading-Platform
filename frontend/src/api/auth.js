import { request } from './client'

export function login(email, password) {
  return request('/auth/login', { method: 'POST', body: { email, password }, auth: false })
}

export function register(email, password) {
  return request('/auth/register', { method: 'POST', body: { email, password }, auth: false })
}
