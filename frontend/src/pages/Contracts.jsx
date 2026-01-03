import { useQuery } from '@tanstack/react-query'
import { getContracts } from '../api/client'
import DataTable from '../components/DataTable'
import { FileCheck, Plus } from 'lucide-react'
import clsx from 'clsx'

export default function Contracts() {
  const { data: contracts, isLoading, error } = useQuery({
    queryKey: ['contracts'],
    queryFn: getContracts,
  })

  const columns = [
    { key: 'name', header: 'Contract Name' },
    { key: 'producer', header: 'Producer' },
    { key: 'consumer', header: 'Consumer' },
    {
      key: 'status',
      header: 'Status',
      render: (value) => (
        <span className={clsx(
          "badge",
          value === 'active' ? "badge-green" : value === 'draft' ? "badge-yellow" : "badge-red"
        )}>
          {value}
        </span>
      ),
    },
    {
      key: 'compliance',
      header: 'Compliance',
      render: (value) => (
        <div className="flex items-center gap-2">
          <div className="w-16 bg-gray-200 rounded-full h-2">
            <div
              className={clsx(
                "h-2 rounded-full",
                value >= 95 ? "bg-green-500" : value >= 80 ? "bg-yellow-500" : "bg-red-500"
              )}
              style={{ width: `${value}%` }}
            />
          </div>
          <span className="text-sm text-gray-600">{value}%</span>
        </div>
      ),
    },
    { key: 'sla', header: 'SLA' },
    {
      key: 'expires_at',
      header: 'Expires',
      render: (value) => value ? new Date(value).toLocaleDateString() : 'Never',
    },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-lg">
        Failed to load contracts: {error.message}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Contracts</h1>
          <p className="text-gray-500">Manage producer-consumer agreements</p>
        </div>
        <button className="btn btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          New Contract
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 rounded-lg">
              <FileCheck className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Active Contracts</p>
              <p className="text-xl font-bold text-gray-900">
                {contracts?.filter(c => c.status === 'active').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-50 rounded-lg">
              <FileCheck className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Draft Contracts</p>
              <p className="text-xl font-bold text-gray-900">
                {contracts?.filter(c => c.status === 'draft').length || 0}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-50 rounded-lg">
              <FileCheck className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Expiring Soon</p>
              <p className="text-xl font-bold text-gray-900">
                {contracts?.filter(c => {
                  if (!c.expires_at) return false
                  const days = (new Date(c.expires_at) - new Date()) / (1000 * 60 * 60 * 24)
                  return days <= 30 && days > 0
                }).length || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      <DataTable
        data={contracts || []}
        columns={columns}
        emptyMessage="No data contracts found"
      />
    </div>
  )
}
