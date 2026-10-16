import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

export const TOKEN_KEY = 'tariqi.tokens'

export interface Tokens {
  access: string
  refresh: string
}

interface Envelope<T> {
  success: boolean
  message: string
  data: T
}

export interface ApiErrorBody {
  success: false
  message: string
  errors: Record<string, string[]>
}

export function loadTokens(): Tokens | null {
  try {
    const raw = localStorage.getItem(TOKEN_KEY)
    return raw ? (JSON.parse(raw) as Tokens) : null
  } catch {
    return null
  }
}

export function saveTokens(tokens: Tokens | null) {
  try {
    if (tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens))
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* storage unavailable: session lasts until reload */
  }
}

export const http = axios.create({ baseURL: '/api' })

let onSessionExpired: () => void = () => {}
export function setSessionExpiredHandler(fn: () => void) {
  onSessionExpired = fn
}

http.interceptors.request.use((config) => {
  const tokens = loadTokens()
  if (tokens) config.headers.Authorization = `Bearer ${tokens.access}`
  return config
})

// A single in-flight refresh is shared by all requests that got a 401 at the same time.
let refreshing: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const tokens = loadTokens()
  if (!tokens) throw new Error('no refresh token')
  // Plain axios: the refresh call must not go through our own interceptors.
  const res = await axios.post<{ access: string; refresh?: string }>('/api/auth/token/refresh/', {
    refresh: tokens.refresh,
  })
  saveTokens({ access: res.data.access, refresh: res.data.refresh ?? tokens.refresh })
  return res.data.access
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
    const isAuthCall = original?.url?.startsWith('/auth/')
    if (error.response?.status !== 401 || !original || original._retried || isAuthCall) {
      return Promise.reject(error)
    }
    original._retried = true
    try {
      refreshing ??= refreshAccessToken().finally(() => (refreshing = null))
      const access = await refreshing
      original.headers.Authorization = `Bearer ${access}`
      return http(original)
    } catch {
      saveTokens(null)
      onSessionExpired()
      return Promise.reject(error)
    }
  },
)

export async function get<T>(url: string): Promise<T> {
  return (await http.get<Envelope<T>>(url)).data.data
}
export async function post<T>(url: string, body?: unknown): Promise<T> {
  return (await http.post<Envelope<T>>(url, body)).data.data
}
export async function patch<T>(url: string, body?: unknown): Promise<T> {
  return (await http.patch<Envelope<T>>(url, body)).data.data
}

/** Best human-readable message from an API error. */
export function errorMessage(err: unknown, fallback = 'حدث خطأ، حاول مرة أخرى'): string {
  const body = (err as AxiosError<ApiErrorBody>)?.response?.data
  if (!body) return fallback
  const firstField = body.errors && Object.values(body.errors)[0]?.[0]
  return firstField || body.message || fallback
}
