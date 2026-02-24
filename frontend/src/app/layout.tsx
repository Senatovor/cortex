'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import './globals.css'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()

  return (
    <html lang="ru">
      <body>
        <div className="min-h-screen bg-gray-100">
          {/* Верхняя панель */}
          <header className="bg-white shadow">
            <div className="max-w-7xl mx-auto px-4 py-4">
              <h1 className="text-xl font-bold text-gray-900">Vector Database Manager</h1>
            </div>
          </header>

          <div className="flex">
            {/* Боковое меню */}
            <aside className="w-64 bg-white shadow-sm min-h-[calc(100vh-73px)]">
              <nav className="p-4">
                <ul className="space-y-2">
                  <li>
                    <Link
                      href="/"
                      className={`block px-4 py-2 rounded transition-colors ${
                        pathname === '/' 
                          ? 'bg-blue-600 text-white' 
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      🏠 Главная
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/edit"
                      className={`block px-4 py-2 rounded transition-colors ${
                        pathname === '/edit' 
                          ? 'bg-blue-600 text-white' 
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      ✏️ Редактирование точек
                    </Link>
                  </li>
                </ul>
              </nav>
            </aside>

            {/* Основной контент */}
            <main className="flex-1 p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  )
}