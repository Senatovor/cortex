'use client'

import { useState, useEffect } from 'react'

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
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const [backendUrl, setBackendUrl] = useState('http://localhost:5001')
  const [showTooltip, setShowTooltip] = useState(false)

  // Состояния для схемы БД
  const [schema, setSchema] = useState<TableSchema | null>(null)
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())
  const [fieldDescriptions, setFieldDescriptions] = useState<FieldDescriptions>({})
  const [excludedTables, setExcludedTables] = useState<ExcludedTables>({})
  const [schemaError, setSchemaError] = useState('')

  // Загрузка схемы БД при активации ручного режима
  useEffect(() => {
    if (manualInput && !schema) {
      loadSchema()
    }
  }, [manualInput])

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
        throw new Error(`Ошибка загрузки схемы: ${response.status}`)
      }

      const data = await response.json()
      setSchema(data)

      // Инициализируем описания полей пустыми значениями
      const initialDescriptions: FieldDescriptions = {}
      // Инициализируем исключенные таблицы (по умолчанию все доступны)
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

    } catch (err: any) {
      setSchemaError(err.message)
      console.error('Ошибка загрузки схемы:', err)
    } finally {
      setLoadingSchema(false)
    }
  }

  const testConnection = async () => {
    try {
      const response = await fetch(`${backendUrl}/docs`)
      if (response.ok) {
        alert('✅ Бэкенд доступен!')
      } else {
        alert(`❌ Ошибка: ${response.status}`)
      }
    } catch (err: any) {
      alert(`❌ ${err.message}`)
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

  // !!! ИСПРАВЛЕННАЯ ФУНКЦИЯ !!!
  const generateFieldsDescription = (): FieldDescriptions => {
    // Возвращаем только заполненные описания для НЕисключенных таблиц
    const result: FieldDescriptions = {}

    Object.entries(fieldDescriptions).forEach(([tableName, fields]) => {
      // Пропускаем исключенные таблицы - они полностью удаляются из запроса
      if (excludedTables[tableName]) {
        return // полностью пропускаем таблицу
      }

      const filledFields: any = {}
      Object.entries(fields).forEach(([fieldName, fieldData]) => {
        if (fieldData.description.trim()) {
          filledFields[fieldName] = fieldData
        }
      })

      // Добавляем таблицу только если есть заполненные поля
      if (Object.keys(filledFields).length > 0) {
        result[tableName] = filledFields
      }
    })

    return result
  }

  // Подсчет статистики
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
  setResult('')
  setError('')

  try {
    // Базовый запрос с vector_database
    const requestBody: any = {
      vector_database: {
        vector_database: collectionName
      }
    }

    if (manualInput) {
      // Генерируем описания полей
      const fieldsDesc = generateFieldsDescription()

      // Оборачиваем fields_description в еще один объект с ключом fields_description
      if (Object.keys(fieldsDesc).length > 0) {
        requestBody.fields_description = {
          fields_description: fieldsDesc  // Двойная вложенность!
        }
      }
    }

    const url = `${backendUrl}/vector/?flag=${manualInput}`

    console.log('URL:', url)
    console.log('Body:', JSON.stringify(requestBody, null, 2))

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    })

    const data = await response.json()

    if (response.ok) {
      setResult(JSON.stringify(data, null, 2))
    } else {
      setError(JSON.stringify(data, null, 2))
    }
  } catch (err: any) {
    setError(`Ошибка соединения: ${err.message}`)
  } finally {
    setLoading(false)
  }
}

  const stats = getStats()

  return (
    <main className="min-h-screen p-4 bg-gray-100">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Vector Database</h1>

        <div className="bg-white rounded shadow p-4 mb-4">
          <div className="flex gap-2 items-center">
            <input
              type="text"
              value={backendUrl}
              onChange={(e) => setBackendUrl(e.target.value)}
              className="flex-1 px-2 py-1 border rounded text-sm"
              placeholder="URL бэкенда"
            />
            <button
              onClick={testConnection}
              className="px-3 py-1 bg-gray-500 text-white rounded text-sm hover:bg-gray-600"
            >
              Проверить
            </button>
          </div>
        </div>

        <div className="bg-white rounded shadow p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Название коллекции */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Название коллекции <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={collectionName}
                onChange={(e) => setCollectionName(e.target.value)}
                className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-300"
                placeholder="my_collection"
                required
              />
            </div>

            {/* Чекбокс для выбора режима */}
            <div className="flex items-center space-x-2 relative">
              <input
                type="checkbox"
                id="manualInput"
                checked={manualInput}
                onChange={(e) => setManualInput(e.target.checked)}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="manualInput" className="text-sm font-medium text-gray-700">
                Ручной ввод описаний полей
              </label>
              <div
                className="relative"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
              >
                <span className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-gray-300 text-white text-xs cursor-help">?</span>
                {showTooltip && (
                  <div className="absolute left-0 bottom-6 w-64 p-2 bg-gray-800 text-white text-xs rounded shadow-lg z-10">
                    Если чекбокс активен - вы вручную заполняете описания полей. Если неактивен - описания генерируются нейросетью автоматически
                  </div>
                )}
              </div>
            </div>

            {/* Ручной ввод описаний полей */}
            {manualInput && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <h2 className="text-lg font-medium">Описания полей таблиц</h2>
                  {!schema && !loadingSchema && !schemaError && (
                    <button
                      type="button"
                      onClick={loadSchema}
                      className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                    >
                      Загрузить схему БД
                    </button>
                  )}
                </div>

                {/* Статистика по таблицам */}
                {schema && (
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div className="bg-blue-50 p-2 rounded text-center">
                      <span className="font-medium text-blue-700">Всего: {stats.total}</span>
                    </div>
                    <div className="bg-green-50 p-2 rounded text-center">
                      <span className="font-medium text-green-700">Активны: {stats.active}</span>
                    </div>
                    <div className="bg-red-50 p-2 rounded text-center">
                      <span className="font-medium text-red-700">Исключены: {stats.excluded}</span>
                    </div>
                  </div>
                )}

                {/* Состояния загрузки */}
                {loadingSchema && (
                  <div className="text-center py-4">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600"></div>
                    <p className="text-sm text-gray-500 mt-2">Загрузка схемы базы данных...</p>
                  </div>
                )}

                {/* Ошибка загрузки */}
                {schemaError && (
                  <div className="bg-red-50 border border-red-200 rounded p-3">
                    <p className="text-sm text-red-600">Ошибка загрузки схемы: {schemaError}</p>
                    <button
                      type="button"
                      onClick={loadSchema}
                      className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                    >
                      Попробовать снова
                    </button>
                  </div>
                )}

                {/* Схема БД */}
                {schema && Object.keys(schema).length > 0 && (
                  <div className="space-y-2">
                    {Object.entries(schema).map(([tableName, fields]) => (
                      <div key={tableName} className={`border rounded overflow-hidden ${excludedTables[tableName] ? 'opacity-60 bg-gray-50' : ''}`}>
                        {/* Заголовок таблицы */}
                        <div
                          onClick={() => toggleTable(tableName)}
                          className="bg-gray-50 px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-100"
                        >
                          <div className="flex items-center space-x-3">
                            <span className="font-medium text-gray-700">{tableName}</span>
                            <span className="text-xs text-gray-500">
                              {fields.length} полей
                            </span>
                          </div>
                          <div className="flex items-center space-x-4">
                            {/* Чекбокс исключения таблицы */}
                            <div className="flex items-center space-x-1" onClick={(e) => e.stopPropagation()}>
                              <input
                                type="checkbox"
                                id={`exclude-${tableName}`}
                                checked={excludedTables[tableName] || false}
                                onChange={() => toggleTableExclusion(tableName)}
                                className="h-3 w-3 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                              />
                              <label
                                htmlFor={`exclude-${tableName}`}
                                className="text-xs text-gray-600 cursor-help"
                                title="Если чекбокс активен, таблица не будет векторизирована и пользователь не сможет получить к ней доступ"
                              >
                                исключить
                              </label>
                            </div>
                            <span className="text-gray-500">
                              {expandedTables.has(tableName) ? '▼' : '▶'}
                            </span>
                          </div>
                        </div>

                        {/* Поля таблицы (показываем только если таблица не исключена) */}
                        {expandedTables.has(tableName) && !excludedTables[tableName] && (
                          <div className="p-4 space-y-3">
                            {(fields as string[]).map(fieldName => (
                              <div key={`${tableName}-${fieldName}`} className="grid grid-cols-12 gap-3 items-start">
                                {/* Название поля (нередактируемое) */}
                                <div className="col-span-2">
                                  <div className="text-sm font-medium text-gray-600 bg-gray-50 px-2 py-2 rounded">
                                    {fieldName}
                                  </div>
                                </div>

                                {/* Описание поля */}
                                <div className="col-span-7">
                                  <input
                                    type="text"
                                    value={fieldDescriptions[tableName]?.[fieldName]?.description || ''}
                                    onChange={(e) => updateFieldDescription(tableName, fieldName, 'description', e.target.value)}
                                    className="w-full px-2 py-1 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-300"
                                    placeholder={`Описание для ${fieldName}`}
                                  />
                                </div>

                                {/* Конфиденциальность */}
                                <div className="col-span-3">
                                  <div className="flex items-center space-x-2">
                                    <input
                                      type="range"
                                      min="1"
                                      max="10"
                                      value={fieldDescriptions[tableName]?.[fieldName]?.confidentiality || 5}
                                      onChange={(e) => updateFieldDescription(tableName, fieldName, 'confidentiality', parseInt(e.target.value))}
                                      className="w-16"
                                    />
                                    <span className="text-xs w-4">{fieldDescriptions[tableName]?.[fieldName]?.confidentiality || 5}</span>
                                    <span className="text-xs text-gray-400">conf</span>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Сообщение для исключенной таблицы */}
                        {expandedTables.has(tableName) && excludedTables[tableName] && (
                          <div className="p-4 text-center text-sm text-gray-500 italic">
                            Таблица исключена из векторизации и не будет включена в запрос
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Информация о заполнении */}
                {schema && (
                  <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-700">
                    <p>💡 Заполните описания для нужных полей. Исключенные таблицы полностью удаляются из запроса.</p>
                  </div>
                )}
              </div>
            )}

            {/* Информация о режиме генерации */}
            {!manualInput && (
              <div className="bg-blue-50 border border-blue-200 rounded p-3">
                <p className="text-sm text-blue-700">
                  🤖 Режим автоматической генерации: описания полей будут созданы нейросетью на основе структуры базы данных
                </p>
              </div>
            )}

            {/* Превью запроса */}
            <div className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
              <p className="font-medium mb-2">📦 Отправляемые данные:</p>
              <pre className="text-xs overflow-auto max-h-40">
            {JSON.stringify({
              vector_database: {
                vector_database: collectionName || 'collection_name'
              },
              ...(manualInput && schema ? generateFieldsDescription() : {})
            }, null, 2)}
              </pre>
              {manualInput && schema && Object.values(excludedTables).some(v => v) && (
                <p className="text-xs text-gray-500 mt-2">
                  ℹ️ Исключенные таблицы: {Object.entries(excludedTables).filter(([_, excl]) => excl).map(([name]) => name).join(', ')}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || loadingSchema}
              className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Отправка...' : 'Добавить вектор'}
            </button>
          </form>

          {/* Ошибка */}
          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
              <p className="text-red-700 text-sm font-medium mb-1">Ошибка:</p>
              <pre className="text-red-600 text-xs whitespace-pre-wrap overflow-auto max-h-40">
                {error}
              </pre>
            </div>
          )}

          {/* Результат */}
          {result && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded">
              <p className="text-green-700 text-sm font-medium mb-1">Ответ:</p>
              <pre className="text-green-600 text-xs whitespace-pre-wrap overflow-auto max-h-40">
                {result}
              </pre>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}