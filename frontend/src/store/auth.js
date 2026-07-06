// Zustand over Context+useReducer: the token is read outside React (api/client,
// the WebSocket hook), which getState() gives us for free; and over Redux:
// one store, two actions -- Redux's ceremony buys nothing at this scale.

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuth = create(
  persist(
    (set) => ({
      token: null,
      email: null,
      setSession: (token, email) => set({ token, email }),
      logout: () => set({ token: null, email: null }),
    }),
    { name: 'papertrade-auth' },
  ),
)
