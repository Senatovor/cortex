// edit/page.tsx
'use client'

import { useState, useEffect } from 'react'
import {
  Save, X, ChevronDown, ChevronRight,
  Edit, Loader, Database, FileText, Layers
} from 'lucide-react'
import Toast from '../components/Toast'

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
  const [points, setPoints] = useState<Point[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedCollections, setExpandedCollections] = useState<Set<string>>(new Set())
  const [expandedPoints, setExpandedPoints] = useState<Set<string>>(new Set())
  const [editingPoints, setEditingPoints] = useState<Record<string, EditingPoint>>({})
  const [savingPoint, setSavingPoint] = useState<string | null>(null)
  const [backendUrl] = useState('http://localhost:5001')
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
  }

  const loadPoints = async () => {
    setLoading(true)

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
      showToast(err.message, 'error')
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

      const response = await fetch(`${backendUrl}/vector/update_point`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      })

      const data = await response.json()

      if (response.ok) {
        showToast(`Точка ${point.table_name} успешно обновлена`, 'success')
        setEditingPoints(prev => ({
          ...prev,
          [pointId]: {
            ...prev[pointId],
            hasChanges: false
          }
        }))
        loadPoints()
      } else {
        showToast(JSON.stringify(data), 'error')
      }
    } catch (err: any) {
      showToast(`Ошибка сохранения: ${err.message}`, 'error')
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

  const pointsByCollection = points.reduce((acc, point) => {
    if (!acc[point.collection]) {
      acc[point.collection] = []
    }
    acc[point.collection].push(point)
    return acc
  }, {} as Record<string, Point[]>)

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
            Редактирование точек
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Управление метаданными векторных точек
          </p>
        </div>

        {/* Загрузка */}
        {loading && !points.length && (
          <div className="text-center py-12">
            <Loader className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-3" />
            <p className="text-sm text-gray-600">Загрузка точек...</p>
          </div>
        )}

        {/* Список точек */}
        {Object.entries(pointsByCollection).map(([collection, collectionPoints]) => (
          <div key={collection} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            {/* Заголовок коллекции */}
            <div
              onClick={() => toggleCollection(collection)}
              className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <Layers className="w-5 h-5 text-gray-400" />
                <span className="font-medium text-gray-900">{collection}</span>
                <span className="text-xs text-gray-500">
                  {collectionPoints.length} {collectionPoints.length === 1 ? 'точка' : 'точек'}
                </span>
              </div>
              {expandedCollections.has(collection) ? (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-400" />
              )}
            </div>

            {/* Точки коллекции */}
            {expandedCollections.has(collection) && (
              <div className="px-4 pb-4 space-y-3">
                {collectionPoints.map((point) => {
                  const editingPoint = editingPoints[point.id]
                  if (!editingPoint) return null

                  return (
                    <div key={point.id} className="border border-gray-200 rounded-lg overflow-hidden">
                      {/* Заголовок точки */}
                      <div
                        onClick={() => togglePoint(point.id)}
                        className="bg-gray-50 px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-100 transition-colors"
                      >
                        <div className="flex items-center space-x-3">
                          <FileText className="w-4 h-4 text-gray-400" />
                          <span className="font-medium text-gray-900">{point.matadata.table_name}</span>
                          <span className="text-xs text-gray-500">
                            ID: {point.id.slice(0, 8)}...
                          </span>
                          {editingPoint.hasChanges && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                              <Edit className="w-3 h-3 mr-1" />
                              изменения
                            </span>
                          )}
                        </div>
                        {expandedPoints.has(point.id) ? (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronRight className="w-4 h-4 text-gray-400" />
                        )}
                      </div>

                      {/* Поля точки */}
                      {expandedPoints.has(point.id) && (
                        <div className="p-4 space-y-4 bg-white">
                          {Object.entries(editingPoint.fields).map(([fieldName, fieldData]) => (
                            <div key={fieldName} className="space-y-2">
                              <div className="text-sm font-medium text-gray-700">
                                {fieldName}
                              </div>
                              <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                                <div className="lg:col-span-9">
                                  <input
                                    type="text"
                                    value={fieldData.description}
                                    onChange={(e) => updateField(point.id, fieldName, 'description', e.target.value)}
                                    className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-sm placeholder-gray-400"
                                    placeholder="Описание"
                                  />
                                </div>
                                <div className="lg:col-span-3">
                                  <div className="flex items-center space-x-2">
                                    <input
                                      type="range"
                                      min="1"
                                      max="10"
                                      value={fieldData.confidentiality}
                                      onChange={(e) => updateField(point.id, fieldName, 'confidentiality', parseInt(e.target.value))}
                                      className="flex-1"
                                    />
                                    <span className="text-sm font-medium text-gray-700 w-8">
                                      {fieldData.confidentiality}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}

                          {/* Кнопки действий */}
                          {editingPoint.hasChanges && (
                            <div className="flex justify-end space-x-2 pt-4 border-t border-gray-200">
                              <button
                                onClick={() => cancelChanges(point.id)}
                                className="px-3 py-1.5 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center space-x-1"
                              >
                                <X className="w-4 h-4" />
                                <span>Отмена</span>
                              </button>
                              <button
                                onClick={() => savePoint(point.id)}
                                disabled={savingPoint === point.id}
                                className="px-4 py-1.5 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all disabled:opacity-50 text-sm font-medium flex items-center space-x-2"
                              >
                                {savingPoint === point.id ? (
                                  <>
                                    <Loader className="w-4 h-4 animate-spin" />
                                    <span>Сохранение...</span>
                                  </>
                                ) : (
                                  <>
                                    <Save className="w-4 h-4" />
                                    <span>Сохранить</span>
                                  </>
                                )}
                              </button>
                            </div>
                          )}
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
        {!loading && points.length === 0 && (
          <div className="text-center py-12">
            <Database className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">Нет доступных точек для редактирования</p>
          </div>
        )}
      </div>
    </>
  )
}