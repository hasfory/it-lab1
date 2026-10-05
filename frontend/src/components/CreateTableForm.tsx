import { useState } from 'react'
import type { FieldDef } from '../types'

type Props = {
  types: string[]
  onCreate: (name: string, fields: FieldDef[]) => Promise<boolean>
}

export default function CreateTableForm({ types, onCreate }: Props) {
  const [name, setName] = useState('')
  const [fields, setFields] = useState<FieldDef[]>([{ name: '', type: 'integer' }])

  const setField = (i: number, patch: Partial<FieldDef>) =>
    setFields(fields.map((f, k) => (k === i ? { ...f, ...patch } : f)))

  const submit = async () => {
    const ok = await onCreate(name, fields)
    if (ok) {
      setName('')
      setFields([{ name: '', type: 'integer' }])
    }
  }

  return (
    <div className="card">
      <h3>Нова таблиця</h3>
      <input
        placeholder="Назва таблиці"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      {fields.map((f, i) => (
        <div className="field-row" key={i}>
          <input
            placeholder="Поле"
            value={f.name}
            onChange={(e) => setField(i, { name: e.target.value })}
          />
          <select value={f.type} onChange={(e) => setField(i, { type: e.target.value })}>
            {types.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
          <button
            className="icon"
            title="Прибрати поле"
            disabled={fields.length === 1}
            onClick={() => setFields(fields.filter((_, k) => k !== i))}
          >
            ✕
          </button>
        </div>
      ))}
      <div className="btn-row">
        <button onClick={() => setFields([...fields, { name: '', type: 'integer' }])}>
          + Поле
        </button>
        <button className="primary" onClick={submit}>
          Створити таблицю
        </button>
      </div>
    </div>
  )
}