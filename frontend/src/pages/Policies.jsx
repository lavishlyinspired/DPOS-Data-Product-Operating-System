import { useQuery } from '@tanstack/react-query'
import { getPolicies } from '../api/client'
import DataTable from '../components/DataTable'
import { Shield, Plus, CheckCircle, XCircle } from 'lucide-react'
import clsx from 'clsx'

export default function Policies() {
  const { data: policies, isLoading, error } = useQuery({
    queryKey: ['policies'],
    queryFn: getPolicies,
  })

  const columns = [
    {
      key: 'name',
      header: 'Policy Name',
      render: (value) => (
        <span className="font-medium text-gray-900">{value}</span>
      ),
    },
    { key: 'type', header: 'Type' },
    { key: 'scope', header: 'Scope' },
    {
      key: 'enabled',
      header: 'Status',
      render: (value) => (
        <div className="flex items-center gap-2">
          {value ? (
            <>
              <CheckCircle className="w-4 h-4 text-green-500" />
              <span className="text-green-600">Enabled</span>
            </>
          ) : (
            <>
              <XCircle className="w-4 h-4 text-gray-400" />
              <span className="text-gray-500">Disabled</span>
            </>
          )}
        </div>
      ),
    },
    {
      key: 'enforcement',
      header: 'Enforcement',
      render: (value) => (
        <span className={clsx(
          "badge",
          value === 'strict' ? "badge-red" : value === 'warn' ? "badge-yellow" : "badge-primary"
        )}>
          {value}
        </span>
      ),
    },
    { key: 'violations', header: 'Violations (30d)' },
    {
      key: 'last_evaluated',
      header: 'Last Evaluated',
      render: (value) => value ? new Date(value).toLocaleString() : 'Never',
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
        Failed to load policies: {error.message}
      </div>
    )
  }

  const enabledPolicies = policies?.filter(p => p.enabled) || []
  const violationCount = policies?.reduce((acc, p) => acc + (p.violations || 0), 0) || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Policies</h1>
          <p className="text-gray-500">Define and enforce data governance rules</p>
        </div>
        <button className="btn btn-primary">
          <Plus className="w-4 h-4 mr-2" />
          New Policy
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-primary-600" />
            <div>
              <p className="text-sm text-gray-500">Total Policies</p>
              <p className="text-xl font-bold text-gray-900">{policies?.length || 0}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <div>
              <p className="text-sm text-gray-500">Enabled</p>
              <p className="text-xl font-bold text-gray-900">{enabledPolicies.length}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <XCircle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm text-gray-500">Violations (30d)</p>
              <p className="text-xl font-bold text-gray-900">{violationCount}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-yellow-500" />
            <div>
              <p className="text-sm text-gray-500">Strict Enforcement</p>
              <p className="text-xl font-bold text-gray-900">
                {policies?.filter(p => p.enforcement === 'strict').length || 0}
              </p>
            </div>
          </div>
        </div>
      </div>

      <DataTable
        data={policies || []}
        columns={columns}
        emptyMessage="No policies defined"
      />
    </div>
  )
}
