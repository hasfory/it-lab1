import { useState } from 'react'
import type { TableData } from '../types'

const HINTS: Record<string, string> = {
  integer: '12',
  real: '3.14',
  char: 'a',
  string: 'текст',
  complexInteger: '3+4i',
  complexReal: '2.5-1.3i',
}

type Props = {
  table: TableData
  onAdd: (values: Record<string, string>) => Promise<boolean>
  onUpdate: (index: number, values: Record<string, string>) => Promise<boolean>
  onDelete: (index: number) => Promise<boolean>
  onSort: (field: string, descending: boolean) => Promise<boolean>
}

const emptyValues = (table: TableData) =>
  Object.fromEntries(table.fields.map((f) => [f.name, '']))

export default function TableView({ table, onAdd, onUpdate, onDelete, onSort }: Props) {
  const [newRow, setNewRow] = useState<Record<string, string>>(emptyValues(table))
  const [editIndex, setEditIndex] = useState<number | null>(null)
  const [editRow, setEditRow] = useState<Record<string, string>>({})
  const [sortField, setSortField] = useState(table.fields[0]?.name ?? '')
  const [sortDesc, setSortDesc] = useState(false)
  const [sorted, setSorted] = useState<{ field: string; desc: boolean } | null>(null)

  const doSort = async (field: string, desc: boolean) => {
    if (await onSort(field, desc)) setSorted({ field, desc })
  }

  const headerClick = (field: string) => {
    const desc = sorted?.field === field ? !sorted.desc : false
    setSortField(field)
    setSortDesc(desc)
    void doSort(field, desc)
  }

  const add = async () => {
    if (await onAdd(newRow)) setNewRow(emptyValues(table))
  }

  const startEdit = (i: number) => {
    setEditIndex(i)
    setEditRow({ ...table.rows[i] })
  }

  const saveEdit = async () => {
    if (editIndex !== null && (await onUpdate(editIndex, editRow))) setEditIndex(null)
  }

  return (
    <div>
      <div className="card sort-bar">
        <strong>Сортування за полем:</strong>
        <select value={sortField} onChange={(e) => setSortField(e.target.value)}>
          {table.fields.map((f) => (
            <option key={f.name} value={f.name}>
              {f.name} ({f.type})
            </option>
          ))}
        </select>
        <select
          value={sortDesc ? 'desc' : 'asc'}
          onChange={(e) => setSortDesc(e.target.value === 'desc')}
        >
          <option value="asc">за зростанням</option>
          <option value="desc">за спаданням</option>
        </select>
        <button className="primary" onClick={() => void doSort(sortField, sortDesc)}>
          Сортувати
        </button>
        <span className="hint">
          Для complexInteger / complexReal порівняння за модулем числа
        </span>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              {table.fields.map((f) => (
                <th key={f.name} className="sortable" onClick={() => headerClick(f.name)}>
                  {f.name} <span className="type">{f.type}</span>
                  {sorted?.field === f.name ? (sorted.desc ? ' ▼' : ' ▲') : ''}
                </th>
              ))}
              <th>Дії</th>
            </tr>
          </thead>
          <tbody>
            {table.rows.length === 0 && (
              <tr>
                <td colSpan={table.fields.length + 2} className="empty">
                  Таблиця порожня
                </td>
              </tr>
            )}
            {table.rows.map((row, i) =>
              editIndex === i ? (
                <tr key={i} className="editing">
                  <td>{i + 1}</td>
                  {table.fields.map((f) => (
                    <td key={f.name}>
                      <input
                        value={editRow[f.name] ?? ''}
                        placeholder={HINTS[f.type]}
                        onChange={(e) => setEditRow({ ...editRow, [f.name]: e.target.value })}
                      />
                    </td>
                  ))}
                  <td className="actions">
                    <button className="primary" onClick={() => void saveEdit()}>
                      Зберегти
                    </button>
                    <button onClick={() => setEditIndex(null)}>Скасувати</button>
                  </td>
                </tr>
              ) : (
                <tr key={i}>
                  <td>{i + 1}</td>
                  {table.fields.map((f) => (
                    <td key={f.name}>{row[f.name]}</td>
                  ))}
                  <td className="actions">
                    <button onClick={() => startEdit(i)}>Змінити</button>
                    <button className="danger" onClick={() => void onDelete(i)}>
                      Видалити
                    </button>
                  </td>
                </tr>
              ),
            )}
          </tbody>
          <tfoot>
            <tr className="add-row">
              <td>+</td>
              {table.fields.map((f) => (
                <td key={f.name}>
                  <input
                    value={newRow[f.name] ?? ''}
                    placeholder={`напр. ${HINTS[f.type] ?? ''}`}
                    onChange={(e) => setNewRow({ ...newRow, [f.name]: e.target.value })}
                    onKeyDown={(e) => e.key === 'Enter' && void add()}
                  />
                </td>
              ))}
              <td className="actions">
                <button className="primary" onClick={() => void add()}>
                  Додати рядок
                </button>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}