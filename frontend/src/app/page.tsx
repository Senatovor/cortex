// page.tsx
'use client'

import { useState, useEffect } from 'react'
import {
  Zap, ChevronDown, ChevronRight,
  Database, Table, Eye, EyeOff, Sliders, Loader
} from 'lucide-react'
import Toast from './components/Toast'

interface TableSchema {
  [tableName: string]: string[]
}

interface FieldDescription {
  description: string
  confidentiality: number
}

interface FieldDescriptions {
  [tableName: string]: {
    [fieldName: string]: FieldDescription
  }
}

interface ExcludedTables {
  [tableName: string]: boolean
}

export default function Home() {
  const [collectionName, setCollectionName] = useState('')
  const [manualInput, setManualInput] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingSchema, setLoadingSchema] = useState(false)
  const [backendUrl, setBackendUrl] = useState('http://localhost:5001')
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const [schema, setSchema] = useState<TableSchema | null>(null)
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())
  const [fieldDescriptions, setFieldDescriptions] = useState<FieldDescriptions>({})
  const [excludedTables, setExcludedTables] = useState<ExcludedTables>({})
  const [schemaError, setSchemaError] = useState('')

  useEffect(() => {
    if (manualInput && !schema) {
      loadSchema()
    }
  }, [manualInput])

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
  }

  const loadSchema = async () => {
    setLoadingSchema(true)
    setSchemaError('')

    try {
      const response = await fetch(`${backendUrl}/vector/schema`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Ошибка загрузки: ${response.status}`)
      }

      const data = await response.json()
      setSchema(data)

      const initialDescriptions: FieldDescriptions = {}
      const initialExcluded: ExcludedTables = {}

      Object.entries(data).forEach(([tableName, fields]) => {
        initialDescriptions[tableName] = {}
        initialExcluded[tableName] = false

        ;(fields as string[]).forEach(fieldName => {
          initialDescriptions[tableName][fieldName] = {
            description: '',
            confidentiality: 5
          }
        })
      })

      setFieldDescriptions(initialDescriptions)
      setExcludedTables(initialExcluded)
      showToast('Схема успешно загружена', 'success')

    } catch (err: any) {
      setSchemaError(err.message)
      showToast(err.message, 'error')
      console.error('Ошибка загрузки схемы:', err)
    } finally {
      setLoadingSchema(false)
    }
  }

  const testConnection = async () => {
    try {
      const response = await fetch(`${backendUrl}/docs`)
      if (response.ok) {
        showToast('Бэкенд доступен', 'success')
      } else {
        showToast(`Ошибка: ${response.status}`, 'error')
      }
    } catch (err: any) {
      showToast(err.message, 'error')
    }
  }

  const toggleTable = (tableName: string) => {
    const newExpanded = new Set(expandedTables)
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName)
    } else {
      newExpanded.add(tableName)
    }
    setExpandedTables(newExpanded)
  }

  const toggleTableExclusion = (tableName: string) => {
    setExcludedTables(prev => ({
      ...prev,
      [tableName]: !prev[tableName]
    }))
  }

  const updateFieldDescription = (
    tableName: string,
    fieldName: string,
    key: keyof FieldDescription,
    value: string | number
  ) => {
    setFieldDescriptions(prev => ({
      ...prev,
      [tableName]: {
        ...prev[tableName],
        [fieldName]: {
          ...prev[tableName]?.[fieldName],
          [key]: value
        }
      }
    }))
  }

  const generateFieldsDescription = (): FieldDescriptions => {
    const result: FieldDescriptions = {}

    Object.entries(fieldDescriptions).forEach(([tableName, fields]) => {
      if (excludedTables[tableName]) {
        return
      }

      const filledFields: any = {}
      Object.entries(fields).forEach(([fieldName, fieldData]) => {
        if (fieldData.description.trim()) {
          filledFields[fieldName] = fieldData
        }
      })

      if (Object.keys(filledFields).length > 0) {
        result[tableName] = filledFields
      }
    })

    return result
  }

  const getStats = () => {
    if (!schema) return { total: 0, excluded: 0, active: 0 }

    const total = Object.keys(schema).length
    const excluded = Object.values(excludedTables).filter(v => v).length
    const active = total - excluded

    return { total, excluded, active }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const requestBody: any = {
        vector_database: {
          vector_database: collectionName
        }
      }

      if (manualInput) {
        const fieldsDesc = generateFieldsDescription()
        if (Object.keys(fieldsDesc).length > 0) {
          requestBody.fields_description = {
            fields_description: fieldsDesc
          }
        }
      }

      const url = `${backendUrl}/vector/?flag=${manualInput}`

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json()

      if (response.ok) {
        showToast('Вектор успешно создан', 'success')
      } else {
        showToast(JSON.stringify(data), 'error')
      }
    } catch (err: any) {
      showToast(`Ошибка соединения: ${err.message}`, 'error')
    } finally {
      setLoading(false)
    }
  }

  const stats = getStats()

  return (
    <>
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}

      <div className="space-y-6">
        {/* Заголовок страницы */}
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Создание вектора
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Преобразуйте структуру базы данных в векторное представление
          </p>
        </div>

        {/* Настройки подключения */}
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-sm placeholder-gray-400"
              placeholder="URL бэкенда"
            />
            <button
              onClick={testConnection}
              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all text-sm font-medium flex items-center space-x-2"
            >
              <Zap className="w-4 h-4" />
              <span>Проверить</span>
            </button>
          </div>
        </div>

        {/* Основная форма */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Название коллекции */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Название коллекции
            </label>
            <input
              type="text"
              value={collectionName}
              onChange={(e) => setCollectionName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 placeholder-gray-400"
              placeholder="my_collection"
              required
            />
            <p className="text-xs text-gray-500 mt-2">
              Имя коллекции в векторной базе данных
            </p>
          </div>

          {/* Режим ввода */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <button
                  type="button"
                  onClick={() => setManualInput(!manualInput)}
                  className={`
                    relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                    ${manualInput ? 'bg-blue-500' : 'bg-gray-300'}
                  `}
                >
                  <span
                    className={`
                      inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                      ${manualInput ? 'translate-x-6' : 'translate-x-1'}
                    `}
                  />
                </button>
                <span className="text-sm font-medium text-gray-700">
                  Ручной ввод описаний
                </span>
              </div>
            </div>

            <div className="mt-3 text-xs text-gray-600 bg-gray-50 p-3 rounded-lg">
              {manualInput
                ? '✏️ Вы сами описываете поля таблиц. Заполните описания для нужных полей, исключенные таблицы не будут обработаны.'
                : '🤖 Автоматическая генерация: описания полей будут созданы нейросетью на основе структуры базы данных'
              }
            </div>
          </div>

          {/* Ручной ввод описаний */}
          {manualInput && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-medium text-gray-900">Схема базы данных</h2>
              </div>

              {/* Статистика */}
              {schema && (
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-blue-50 rounded-lg p-3 text-center">
                    <Database className="w-4 h-4 text-blue-500 mx-auto mb-1" />
                    <span className="text-sm font-medium text-blue-700">{stats.total}</span>
                    <span className="text-xs text-blue-600 block">всего</span>
                  </div>
                  <div className="bg-green-50 rounded-lg p-3 text-center">
                    <Eye className="w-4 h-4 text-green-500 mx-auto mb-1" />
                    <span className="text-sm font-medium text-green-700">{stats.active}</span>
                    <span className="text-xs text-green-600 block">активны</span>
                  </div>
                  <div className="bg-red-50 rounded-lg p-3 text-center">
                    <EyeOff className="w-4 h-4 text-red-500 mx-auto mb-1" />
                    <span className="text-sm font-medium text-red-700">{stats.excluded}</span>
                    <span className="text-xs text-red-600 block">исключены</span>
                  </div>
                </div>
              )}

              {/* Загрузка */}
              {loadingSchema && (
                <div className="text-center py-8">
                  <Loader className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
                  <p className="text-sm text-gray-600">Загрузка схемы базы данных...</p>
                </div>
              )}

              {/* Схема */}
              {schema && Object.keys(schema).length > 0 && (
                <div className="space-y-3">
                  {Object.entries(schema).map(([tableName, fields]) => (
                    <div
                      key={tableName}
                      className={`border border-gray-200 rounded-lg overflow-hidden transition-opacity
                        ${excludedTables[tableName] ? 'opacity-60' : ''}`}
                    >
                      {/* Заголовок таблицы */}
                      <div
                        onClick={() => toggleTable(tableName)}
                        className="bg-gray-50 px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center space-x-3">
                          <Table className="w-4 h-4 text-gray-400" />
                          <span className="font-medium text-gray-900">{tableName}</span>
                          <span className="text-xs text-gray-500">
                            {fields.length} {fields.length === 1 ? 'поле' : 'полей'}
                          </span>
                        </div>
                        <div className="flex items-center space-x-4">
                          <div onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              onClick={() => toggleTableExclusion(tableName)}
                              className={`p-1 rounded transition-colors ${
                                excludedTables[tableName]
                                  ? 'text-red-500 hover:bg-red-50'
                                  : 'text-gray-400 hover:bg-gray-200'
                              }`}
                              title={excludedTables[tableName] ? 'Включить таблицу' : 'Исключить таблицу'}
                            >
                              {excludedTables[tableName] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                          </div>
                          {expandedTables.has(tableName) ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </div>
                      </div>

                      {/* Поля таблицы */}
                      {expandedTables.has(tableName) && !excludedTables[tableName] && (
                        <div className="p-4 space-y-4 bg-white">
                          {(fields as string[]).map(fieldName => (
                            <div key={`${tableName}-${fieldName}`} className="space-y-2">
                              <div className="text-sm font-medium text-gray-700">
                                {fieldName}
                              </div>
                              <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                                <div className="lg:col-span-8">
                                  <input
                                    type="text"
                                    value={fieldDescriptions[tableName]?.[fieldName]?.description || ''}
                                    onChange={(e) => updateFieldDescription(tableName, fieldName, 'description', e.target.value)}
                                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-sm placeholder-gray-400"
                                    placeholder={`Описание для ${fieldName}`}
                                  />
                                </div>
                                <div className="lg:col-span-4">
                                  <div className="flex items-center space-x-3">
                                    <Sliders className="w-4 h-4 text-gray-400" />
                                    <input
                                      type="range"
                                      min="1"
                                      max="10"
                                      value={fieldDescriptions[tableName]?.[fieldName]?.confidentiality || 5}
                                      onChange={(e) => updateFieldDescription(tableName, fieldName, 'confidentiality', parseInt(e.target.value))}
                                      className="flex-1"
                                    />
                                    <span className="text-sm font-medium text-gray-700 w-8">
                                      {fieldDescriptions[tableName]?.[fieldName]?.confidentiality || 5}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Сообщение для исключенной таблицы */}
                      {expandedTables.has(tableName) && excludedTables[tableName] && (
                        <div className="p-4 text-center text-sm text-gray-500 italic bg-white">
                          Таблица исключена из обработки
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Кнопка отправки */}
          <button
            type="submit"
            disabled={loading || loadingSchema}
            className="w-full py-4 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-medium hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/25"
          >
            {loading ? (
              <div className="flex items-center justify-center space-x-2">
                <Loader className="w-5 h-5 animate-spin" />
                <span>Обработка...</span>
              </div>
            ) : (
              'Создать вектор'
            )}
          </button>
        </form>
      </div>
    </>
  )
}