const TOKEN_KEY = 'qa_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string | null) => (t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY))

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const t = getToken()
  if (t) headers.Authorization = `Bearer ${t}`
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(`/api${path}`, {
    method: opts.method ?? (opts.body !== undefined || opts.form ? 'POST' : 'GET'),
    headers,
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
  })
  if (res.status === 401 && t && !path.startsWith('/auth/login')) {
    setToken(null)
    window.location.href = '/login'
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail)
  }
  return res.json()
}

export const CATEGORY_LABEL: Record<string, string> = {
  foreign_object: 'Foreign object',
  allergen_labeling: 'Allergen / labeling',
  spoilage_freshness: 'Spoilage / freshness',
  cold_chain: 'Cold chain',
  taste_texture: 'Taste / texture',
  packaging_damage: 'Packaging damage',
  missing_item: 'Missing / wrong item',
  shipping_delivery: 'Shipping / delivery',
  billing: 'Billing',
  praise_other: 'Praise / other',
}

export const SEV_COLOR: Record<string, string> = {
  low: '#9cb89b',
  medium: '#f2b33d',
  high: '#d9622b',
  critical: '#b3261e',
}

export const fmtDate = (iso: string) =>
  new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
