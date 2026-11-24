import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken } from './api'

export type User = { id: number; email: string; name: string; role: string }
type Ctx = { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => void }

const AuthCtx = createContext<Ctx>(null as unknown as Ctx)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api<User>('/auth/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const r = await api<{ token: string; user: User }>('/auth/login', { body: { email, password } })
    setToken(r.token)
    setUser(r.user)
  }
  const logout = () => {
    setToken(null)
    setUser(null)
  }
  return <AuthCtx.Provider value={{ user, loading, login, logout }}>{children}</AuthCtx.Provider>
}

/** Which sections each role can see (mirrors the API's role checks). */
export const ACCESS: Record<string, string[]> = {
  complaints: ['support', 'quality', 'executive', 'admin'],
  issues: ['support', 'quality', 'executive', 'admin'],
  reports: ['support', 'quality', 'executive', 'admin'],
  intake: ['support', 'quality', 'admin'],
  admin: ['admin'],
}
export const can = (role: string | undefined, section: string) => !!role && (ACCESS[section]?.includes(role) ?? true)
