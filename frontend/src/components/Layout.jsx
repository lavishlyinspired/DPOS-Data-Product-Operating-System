import { Outlet, NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Database,
  FolderTree,
  FileCheck,
  AlertTriangle,
  GitBranch,
  Workflow,
  Shield,
  Search,
  Bot,
  Brain,
  Upload,
  Menu,
  X,
  UserCheck
} from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Products', href: '/products', icon: Database },
  { name: 'Domains', href: '/domains', icon: FolderTree },
  { name: 'Contracts', href: '/contracts', icon: FileCheck },
  { name: 'Incidents', href: '/incidents', icon: AlertTriangle },
  { name: 'Lineage', href: '/lineage', icon: GitBranch },
  { name: 'Pipelines', href: '/pipelines', icon: Workflow },
  { name: 'Policies', href: '/policies', icon: Shield },
  { name: 'Marketplace', href: '/marketplace', icon: Search },
  { name: 'AI Agents', href: '/agents', icon: Bot },
  { name: 'Intelligence', href: '/intelligence', icon: Brain },
  { name: 'Data Ingestion', href: '/ingestion', icon: Upload },
  { name: 'Human Review', href: '/human-review', icon: UserCheck },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        "fixed top-0 left-0 z-50 h-full w-64 bg-white border-r border-gray-200 transform transition-transform lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <Database className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-gray-900">DPOS</span>
          </div>
          <button
            className="lg:hidden p-2 text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="p-4 space-y-1">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) => clsx(
                "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-50 text-primary-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-white border-b border-gray-200 flex items-center px-6">
          <button
            className="lg:hidden p-2 -ml-2 text-gray-500 hover:text-gray-700"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-6 h-6" />
          </button>
          <div className="ml-auto text-sm text-gray-500">
            Data Product Operating System
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
