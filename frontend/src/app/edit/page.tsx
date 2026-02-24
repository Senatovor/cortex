'use client'

import { useState, useEffect } from 'react'

interface PointMetadata {
  table_name: string
  value: Record<string, {
    description: string
    confidentiality: number
  }>
}

interface Point {
  id: string
  collection: string
  matadata: PointMetadata
}

interface EditingField {
  description: string
  confidentiality: number
}

interface EditingPoint {
  id: string
  collection: string
  table_name: string
  fields: Record<string, EditingField>
  hasChanges: boolean
}

export default function EditPage() {
  const [backendUrl, setBackendUrl] = useState('http://localhost:5001')
  const [points, setPoints] = useState<Point[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedCollections, setExpandedCollections] = useState<Set<string>>(new Set())
  const [expandedPoints, setExpandedPoints] = useState<Set<string>>(new Set())
  const [editingPoints, setEditingPoints] = useState<Record<string, EditingPoint>>({})
  const [savingPoint, setSavingPoint] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Загрузка точек
  const loadPoints = async () => {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${backendUrl}/vector/points`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error(`Ошибка загрузки: ${response.status}`)
      }

      const data = await response.json()
      setPoints(data)

      // Инициализируем редактируемые точки
      const initialEditing: Record<string, EditingPoint> = {}
      data.forEach((point: Point) => {
        initialEditing[point.id] = {
          id: point.id,
          collection: point.collection,
          table_name: point.matadata.table_name,
          fields: { ...point.matadata.value },
          hasChanges: false
        }
      })
      setEditingPoints(initialEditing)

    } catch (err: any) {
      setError(err.message)
      console.error('Ошибка загрузки точек:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPoints()
  }, [])

  const toggleCollection = (collection: string) => {
    const newExpanded = new Set(expandedCollections)
    if (newExpanded.has(collection)) {
      newExpanded.delete(collection)
    } else {
      newExpanded.add(collection)
    }
    setExpandedCollections(newExpanded)
  }

  const togglePoint = (pointId: string) => {
    const newExpanded = new Set(expandedPoints)
    if (newExpanded.has(pointId)) {
      newExpanded.delete(pointId)
    } else {
      newExpanded.add(pointId)
    }
    setExpandedPoints(newExpanded)
  }

  const updateField = (
    pointId: string,
    fieldName: string,
    key: keyof EditingField,
    value: string | number
  ) => {
    setEditingPoints(prev => ({
      ...prev,
      [pointId]: {
        ...prev[pointId],
        fields: {
          ...prev[pointId].fields,
          [fieldName]: {
            ...prev[pointId].fields[fieldName],
            [key]: key === 'confidentiality' ? Number(value) : value
          }
        },
        hasChanges: true
      }
    }))
  }

  const savePoint = async (pointId: string) => {
    const point = editingPoints[pointId]
    if (!point) return

    setSavingPoint(pointId)
    setError('')
    setSuccess('')

    try {
      const requestBody = {
        point: {
          id: pointId,
          table_name: point.table_name,
          value: point.fields
        },
        collection_name: {
          vector_database: point.collection
        }
      }

      console.log('Saving point:', requestBody)

      const response = await fetch(`${backendUrl}/vector/update_point`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess(`Точка ${point.table_name} успешно обновлена`)
        // Сбрасываем флаг изменений
        setEditingPoints(prev => ({
          ...prev,
          [pointId]: {
            ...prev[pointId],
            hasChanges: false
          }
        }))
        // Перезагружаем точки
        loadPoints()
      } else {
        setError(JSON.stringify(data, null, 2))
      }
    } catch (err: any) {
      setError(`Ошибка сохранения: ${err.message}`)
    } finally {
      setSavingPoint(null)
    }
  }

  const cancelChanges = (pointId: string) => {
    const originalPoint = points.find(p => p.id === pointId)
    if (originalPoint) {
      setEditingPoints(prev => ({
        ...prev,
        [pointId]: {
          id: pointId,
          collection: originalPoint.collection,
          table_name: originalPoint.matadata.table_name,
          fields: { ...originalPoint.matadata.value },
          hasChanges: false
        }
      }))
    }
  }

  // Группируем точки по коллекциям
  const pointsByCollection = points.reduce((acc, point) => {
    if (!acc[point.collection]) {
      acc[point.collection] = []
    }
    acc[point.collection].push(point)
    return acc
  }, {} as Record<string, Point[]>)

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Редактирование точек</h1>
        <button
          onClick={loadPoints}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Загрузка...' : '🔄 Обновить'}
        </button>
      </div>

      {/* Настройки подключения */}
      <div className="bg-white rounded shadow p-4">
        <div className="flex gap-2 items-center">
          <input
            type="text"
            value={backendUrl}
            onChange={(e) => setBackendUrl(e.target.value)}
            className="flex-1 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-300"
            placeholder="URL бэкенда"
          />
          <button
            onClick={() => loadPoints()}
            className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          >
            Подключиться
          </button>
        </div>
      </div>

      {/* Ошибка */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-4">
          <p className="text-red-700 font-medium mb-1">Ошибка:</p>
          <pre className="text-red-600 text-sm whitespace-pre-wrap">{error}</pre>
        </div>
      )}

      {/* Успех */}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded p-4">
          <p className="text-green-700">{success}</p>
        </div>
      )}

      {/* Загрузка */}
      {loading && !points.length && (
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-3 border-gray-300 border-t-blue-600"></div>
          <p className="text-gray-500 mt-2">Загрузка точек...</p>
        </div>
      )}

      {/* Список точек по коллекциям */}
      {Object.entries(pointsByCollection).map(([collection, collectionPoints]) => (
        <div key={collection} className="bg-white rounded shadow overflow-hidden">
          {/* Заголовок коллекции */}
          <div
            onClick={() => toggleCollection(collection)}
            className="bg-gray-50 px-6 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-100"
          >
            <div className="flex items-center space-x-3">
              <span className="font-semibold text-gray-800">{collection}</span>
              <span className="text-sm text-gray-500">({collectionPoints.length} точек)</span>
            </div>
            <span className="text-gray-500">
              {expandedCollections.has(collection) ? '▼' : '▶'}
            </span>
          </div>

          {/* Точки коллекции */}
          {expandedCollections.has(collection) && (
            <div className="p-4 space-y-3">
              {collectionPoints.map((point) => {
                const editingPoint = editingPoints[point.id]
                if (!editingPoint) return null

                return (
                  <div key={point.id} className="border rounded overflow-hidden">
                    {/* Заголовок точки */}
                    <div
                      onClick={() => togglePoint(point.id)}
                      className="bg-white px-4 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-50 border-b"
                    >
                      <div className="flex items-center space-x-3">
                        <span className="font-medium text-gray-700">{point.matadata.table_name}</span>
                        <span className="text-xs text-gray-500">ID: {point.id.slice(0, 8)}...</span>
                        {editingPoint.hasChanges && (
                          <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded">
                            ✏️ Есть изменения
                          </span>
                        )}
                      </div>
                      <span className="text-gray-500">
                        {expandedPoints.has(point.id) ? '▼' : '▶'}
                      </span>
                    </div>

                    {/* Поля точки */}
                    {expandedPoints.has(point.id) && (
                      <div className="p-4 bg-gray-50">
                        <div className="space-y-3">
                          {/* Заголовки */}
                          <div className="grid grid-cols-12 gap-3 px-2 text-xs font-medium text-gray-500">
                            <div className="col-span-3">Поле</div>
                            <div className="col-span-7">Описание</div>
                            <div className="col-span-2">Конфиденц.</div>
                          </div>

                          {/* Поля */}
                          {Object.entries(editingPoint.fields).map(([fieldName, fieldData]) => (
                            <div key={fieldName} className="grid grid-cols-12 gap-3 items-center">
                              <div className="col-span-3">
                                <div className="text-sm font-medium text-gray-600 bg-white px-2 py-2 rounded border">
                                  {fieldName}
                                </div>
                              </div>
                              <div className="col-span-7">
                                <input
                                  type="text"
                                  value={fieldData.description}
                                  onChange={(e) => updateField(point.id, fieldName, 'description', e.target.value)}
                                  className="w-full px-2 py-1 border rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-300"
                                  placeholder="Описание"
                                />
                              </div>
                              <div className="col-span-2">
                                <div className="flex items-center space-x-2">
                                  <input
                                    type="range"
                                    min="1"
                                    max="10"
                                    value={fieldData.confidentiality}
                                    onChange={(e) => updateField(point.id, fieldName, 'confidentiality', parseInt(e.target.value))}
                                    className="w-16"
                                  />
                                  <span className="text-xs w-4">{fieldData.confidentiality}</span>
                                </div>
                              </div>
                            </div>
                          ))}

                          {/* Кнопки действий */}
                          <div className="flex justify-end space-x-2 mt-4 pt-3 border-t">
                            {editingPoint.hasChanges && (
                              <>
                                <button
                                  onClick={() => cancelChanges(point.id)}
                                  className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-100"
                                >
                                  Отмена
                                </button>
                                <button
                                  onClick={() => savePoint(point.id)}
                                  disabled={savingPoint === point.id}
                                  className="px-4 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50 flex items-center space-x-1"
                                >
                                  {savingPoint === point.id ? (
                                    <>
                                      <span className="inline-block animate-spin rounded-full h-3 w-3 border-2 border-white border-t-transparent"></span>
                                      <span>Сохранение...</span>
                                    </>
                                  ) : (
                                    <span>💾 Принять изменения</span>
                                  )}
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      ))}

      {/* Нет данных */}
      {!loading && points.length === 0 && !error && (
        <div className="bg-white rounded shadow p-8 text-center text-gray-500">
          Нет доступных точек для редактирования
        </div>
      )}
    </div>
  )
}