export type FieldDef = { name: string; type: string }

export type TableSummary = {
  name: string
  fields: FieldDef[]
  row_count: number
}

export type TableData = {
  name: string
  fields: FieldDef[]
  rows: Record<string, string>[]
}

export type DbInfo = { name: string; tables: string[] }

export type Message = { kind: 'ok' | 'err'; text: string }