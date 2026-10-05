import type { DbInfo, FieldDef, TableData, TableSummary } from './types'

const SERVER_KEY = 'tabledb.server'
const SESSION_KEY = 'tabledb.session'
export const DEFAULT_SERVER = 'http://127.0.0.1:8000'

/** Веб-версія (npm run build:web): інтерфейс і API на одній адресі. */
export const IS_WEB = import.meta.env.VITE_WEB === 'true'

export function getServer(): string {
  if (IS_WEB) return '' // той самий origin, відносні шляхи
  return localStorage.getItem(SERVER_KEY) || DEFAULT_SERVER
}

export function setServer(url: string): void {
  localStorage.setItem(SERVER_KEY, url.trim().replace(/\/+$/, '') || DEFAULT_SERVER)
}

/** Ідентифікатор сесії браузера: створюється один раз і зберігається в localStorage. */
export function getSessionId(): string {
  let id = localStorage.getItem(SESSION_KEY)
  if (!id) {
    const bytes = crypto.getRandomValues(new Uint8Array(16))
    id = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')
    localStorage.setItem(SESSION_KEY, id)
  }
  return id
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (IS_WEB) headers['X-Session-Id'] = getSessionId()

  let res: Response
  try {
    res = await fetch(getServer() + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new Error(
      IS_WEB ? "Не вдалося з'єднатися із сервером" : `Не вдалося з'єднатися із сервером ${getServer()}`,
    )
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = data?.detail
    throw new Error(typeof detail === 'string' ? detail : `Помилка запиту (${res.status})`)
  }
  return data as T
}

const t = (name: string) => encodeURIComponent(name)

export const api = {
  types: () => request<string[]>('GET', '/api/types'),
  database: () => request<DbInfo>('GET', '/api/database'),
  newDatabase: (name: string) => request<DbInfo>('POST', '/api/database', { name }),
  files: () => request<string[]>('GET', '/api/database/files'),
  save: (filename: string) => request<{ saved: string }>('POST', '/api/database/save', { filename }),
  load: (filename: string) => request<DbInfo>('POST', '/api/database/load', { filename }),
  exportDb: () => request<Record<string, unknown>>('GET', '/api/database/export'),
  importDb: (data: unknown) => request<DbInfo>('POST', '/api/database/import', data),
  tables: () => request<TableSummary[]>('GET', '/api/tables'),
  createTable: (name: string, fields: FieldDef[]) =>
    request<TableData>('POST', '/api/tables', { name, fields }),
  getTable: (name: string) => request<TableData>('GET', `/api/tables/${t(name)}`),
  deleteTable: (name: string) => request<{ deleted: string }>('DELETE', `/api/tables/${t(name)}`),
  addRow: (name: string, values: Record<string, string>) =>
    request<TableData>('POST', `/api/tables/${t(name)}/rows`, { values }),
  updateRow: (name: string, index: number, values: Record<string, string>) =>
    request<TableData>('PUT', `/api/tables/${t(name)}/rows/${index}`, { values }),
  deleteRow: (name: string, index: number) =>
    request<TableData>('DELETE', `/api/tables/${t(name)}/rows/${index}`),
  sort: (name: string, field: string, descending: boolean) =>
    request<TableData>('POST', `/api/tables/${t(name)}/sort`, { field, descending }),
}
