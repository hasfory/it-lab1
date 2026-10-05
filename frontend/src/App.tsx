import { useCallback, useEffect, useRef, useState } from 'react'
import { api, DEFAULT_SERVER, getServer, getSessionId, IS_WEB, setServer } from './api'
import CreateTableForm from './components/CreateTableForm'
import TableView from './components/TableView'
import type { DbInfo, FieldDef, Message, TableData, TableSummary } from './types'

export default function App() {
  const [serverUrl, setServerUrl] = useState(getServer())
  const [db, setDb] = useState<DbInfo | null>(null)
  const [tables, setTables] = useState<TableSummary[]>([])
  const [types, setTypes] = useState<string[]>([])
  const [files, setFiles] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [table, setTable] = useState<TableData | null>(null)
  const [message, setMessage] = useState<Message | null>(null)
  const [newDbName, setNewDbName] = useState('')
  const [saveName, setSaveName] = useState('')
  const [loadName, setLoadName] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  /** Виконує дію, показує повідомлення про успіх або помилку. */
  const run = useCallback(async (action: () => Promise<unknown>, okText?: string) => {
    try {
      await action()
      if (okText) setMessage({ kind: 'ok', text: okText })
      return true
    } catch (e) {
      setMessage({ kind: 'err', text: e instanceof Error ? e.message : String(e) })
      return false
    }
  }, [])

  const refresh = useCallback(async () => {
    const [info, list, fileList] = await Promise.all([api.database(), api.tables(), api.files()])
    setDb(info)
    setTables(list)
    setFiles(fileList)
    setLoadName((cur) => (fileList.includes(cur) ? cur : (fileList[0] ?? '')))
    setSelected((cur) => (cur && info.tables.includes(cur) ? cur : null))
  }, [])

  const connect = useCallback(async () => {
    await run(async () => {
      setTypes(await api.types())
      await refresh()
    })
  }, [refresh, run])

  useEffect(() => {
    void connect()
  }, [connect])

  useEffect(() => {
    if (!selected) {
      setTable(null)
      return
    }
    api.getTable(selected).then(setTable).catch(() => setTable(null))
  }, [selected])

  // ---- дії -----------------------------------------------------------------
  const changeServer = async () => {
    setMessage(null)
    setServer(serverUrl)
    setServerUrl(getServer())
    setSelected(null)
    await connect()
    setMessage((m) => m ?? { kind: 'ok', text: `Підключено до ${getServer()}` })
  }

  const createDb = () =>
    run(async () => {
      await api.newDatabase(newDbName)
      setNewDbName('')
      setSelected(null)
      await refresh()
    }, 'Створено нову базу')

  const saveDb = () =>
    run(async () => {
      const r = await api.save(saveName)
      await refresh()
      setMessage({ kind: 'ok', text: `Базу збережено у файл ${r.saved}` })
    })

  const loadDb = () =>
    run(async () => {
      await api.load(loadName)
      setSelected(null)
      await refresh()
    }, `Базу завантажено з файлу ${loadName}`)

  /** Зберігає базу у файл на комп'ютері користувача (завантаження через браузер). */
  const exportDb = () =>
    run(async () => {
      const data = await api.exportDb()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${db?.name ?? 'database'}.json`
      a.click()
      URL.revokeObjectURL(url)
      setMessage({ kind: 'ok', text: `Базу збережено у файл ${a.download} на вашому комп'ютері` })
    })

  /** Читає файл бази, вибраний користувачем, і замінює поточну базу. */
  const importDb = (file: File) =>
    run(async () => {
      let data: unknown
      try {
        data = JSON.parse(await file.text())
      } catch {
        throw new Error('Файл не є коректним JSON')
      }
      await api.importDb(data)
      setSelected(null)
      await refresh()
      setMessage({ kind: 'ok', text: `Базу завантажено з файлу ${file.name}` })
    })

  const createTable = (name: string, fields: FieldDef[]) =>
    run(async () => {
      await api.createTable(name, fields)
      await refresh()
      setSelected(name)
    }, `Таблицю «${name}» створено`)

  const deleteTable = (name: string) =>
    run(async () => {
      if (!window.confirm(`Видалити таблицю «${name}»?`)) return
      await api.deleteTable(name)
      await refresh()
      if (selected === name) setSelected(null)
      setMessage({ kind: 'ok', text: `Таблицю «${name}» видалено` })
    })

  /** Для операцій над рядками: виконує запит і оновлює таблицю. */
  const tableAction = (call: () => Promise<TableData>, okText: string) =>
    run(async () => {
      setTable(await call())
      await refresh()
    }, okText)

  return (
    <div className="app">
      <header>
        <h1>Табличні бази даних</h1>
        {IS_WEB ? (
          <div className="session" title="Кожен браузер працює у власній сесії">
            Ваша сесія: <code>{getSessionId().slice(0, 8)}</code>
          </div>
        ) : (
          <div className="server">
            <label>Сервер:</label>
            <input value={serverUrl} onChange={(e) => setServerUrl(e.target.value)} />
            <button onClick={() => void changeServer()}>Підключитися</button>
            <button onClick={() => setServerUrl(DEFAULT_SERVER)} title="Локальний сервер">
              Локальний
            </button>
          </div>
        )}
      </header>

      {message && (
        <div className={`message ${message.kind}`} onClick={() => setMessage(null)}>
          {message.text}
        </div>
      )}

      <section className="card toolbar">
        <div className="toolbar-row">
          <strong>База: {db ? db.name : '—'}</strong>
          <input
            placeholder="Назва нової бази"
            value={newDbName}
            onChange={(e) => setNewDbName(e.target.value)}
          />
          <button onClick={() => void createDb()}>Створити базу</button>
        </div>
        <div className="toolbar-row">
          <span className="group-label">Файли на сервері:</span>
          <input
            placeholder="Ім'я файлу"
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
          />
          <button onClick={() => void saveDb()}>Зберегти на сервері</button>
          <select value={loadName} onChange={(e) => setLoadName(e.target.value)}>
            {files.length === 0 && <option value="">(немає файлів)</option>}
            {files.map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
          <button disabled={!loadName} onClick={() => void loadDb()}>
            Завантажити з сервера
          </button>
        </div>
        <div className="toolbar-row">
          <span className="group-label">Файл на вашому комп'ютері:</span>
          <button onClick={() => void exportDb()}>Експортувати у файл</button>
          <button onClick={() => fileInput.current?.click()}>Імпортувати з файлу</button>
          <input
            ref={fileInput}
            type="file"
            accept=".json,application/json"
            hidden
            onChange={(e) => {
              const file = e.target.files?.[0]
              e.target.value = ''
              if (file) void importDb(file)
            }}
          />
        </div>
      </section>

      <div className="layout">
        <aside>
          <div className="card">
            <h3>Таблиці</h3>
            {tables.length === 0 && <p className="empty">Таблиць ще немає</p>}
            <ul className="tables">
              {tables.map((t) => (
                <li key={t.name} className={t.name === selected ? 'active' : ''}>
                  <button className="link" onClick={() => setSelected(t.name)}>
                    {t.name}
                    <span className="meta">
                      {t.fields.length} полів, {t.row_count} рядків
                    </span>
                  </button>
                  <button className="icon danger" title="Видалити таблицю" onClick={() => void deleteTable(t.name)}>
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <CreateTableForm types={types} onCreate={createTable} />
        </aside>

        <main>
          {table ? (
            <>
              <h2>Таблиця «{table.name}»</h2>
              <TableView
                key={table.name + table.fields.map((f) => f.name + f.type).join()}
                table={table}
                onAdd={(values) => tableAction(() => api.addRow(table.name, values), 'Рядок додано')}
                onUpdate={(i, values) =>
                  tableAction(() => api.updateRow(table.name, i, values), 'Рядок змінено')
                }
                onDelete={(i) => tableAction(() => api.deleteRow(table.name, i), 'Рядок видалено')}
                onSort={(field, desc) =>
                  tableAction(
                    () => api.sort(table.name, field, desc),
                    `Відсортовано за полем «${field}» ${desc ? 'за спаданням' : 'за зростанням'}`,
                  )
                }
              />
            </>
          ) : (
            <p className="empty big">Оберіть таблицю зліва або створіть нову</p>
          )}
        </main>
      </div>
    </div>
  )
}
