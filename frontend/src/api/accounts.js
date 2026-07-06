import { request } from './client'

export function getMyAccount() {
  return request('/accounts/me')
}
