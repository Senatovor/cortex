// layout.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Menu, X, Cpu, Home, Edit, Database, ChevronRight } from 'lucide-react'
import './globals.css'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  const navigation = [
    { name: 'Главная', href: '/', icon: Home },
    { name: 'Редактирование точек', href: '/edit', icon: Edit },
  ]

  return (
    <html lang="ru" className="h-full">
      <body className="h-full antialiased bg-gray-50">
        <div className="min-h-full flex">
          {/* Затемнение фона при открытом сайдбаре */}
          {isSidebarOpen && (
            <div
              className="fixed inset-0 bg-black/20 backdrop-blur-sm z-20"
              onClick={() => setIsSidebarOpen(false)}
            />
          )}

          {/* Левая панель с кнопкой и логотипом */}
          <div className="fixed top-0 left-0 z-10 flex items-center h-16 px-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <Menu className="w-5 h-5 text-gray-600" />
            </button>

            {/* Иконка CORTEX (видна только когда меню закрыто) */}
            {!isSidebarOpen && (
              <div className="ml-1 flex items-center">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                  <Cpu className="w-4 h-4 text-white" />
                </div>
              </div>
            )}
          </div>

          {/* Сайдбар */}
          <aside
            className={`
              fixed inset-y-0 left-0 z-30
              flex flex-col w-72
              bg-white
              border-r border-gray-200
              transform transition-transform duration-300 ease-in-out
              ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
            `}
          >
            {/* Заголовок сайдбара */}
            <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                  <Cpu className="w-4 h-4 text-white" />
                </div>
                <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  CORTEX
                </span>
              </div>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Навигация */}
            <nav className="flex-1 px-2 py-4 space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setIsSidebarOpen(false)}
                    className={`
                      flex items-center space-x-3 px-4 py-3 rounded-lg
                      transition-all duration-200
                      ${isActive
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-gray-700 hover:bg-gray-100'
                      }
                    `}
                  >
                    <Icon className={`w-5 h-5 ${isActive ? 'text-blue-500' : 'text-gray-400'}`} />
                    <span className="font-medium">{item.name}</span>
                    {isActive && (
                      <ChevronRight className="w-4 h-4 ml-auto text-blue-500" />
                    )}
                  </Link>
                )
              })}
            </nav>

            {/* Нижняя часть сайдбара */}
            <div className="p-4 border-t border-gray-200">
              <div className="flex items-center space-x-3 px-4 py-3 text-gray-500">
                <Database className="w-5 h-5" />
                <span className="text-sm">Версия 1.0.0</span>
              </div>
            </div>
          </aside>

          {/* Основной контент */}
          <main className="flex-1 min-w-0 pl-16">
            <div className="max-w-5xl mx-auto p-6">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  )
}