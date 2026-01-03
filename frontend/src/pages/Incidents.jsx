import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getIncidents, handleIncident } from '../api/client'
import DataTable from '../components/DataTable'
import { AlertTriangle, CheckCircle, Clock, Zap } from 'lucide-react'
import clsx from 'clsx'

export default function Incidents() {
  const queryClient = useQueryClient()
  const [selectedIncident, setSelectedIncident] = useState(null)

  const { data: incidents, isLoading, error } = useQuery({
    queryKey: ['incidents'],
    queryFn: getIncidents,
    refetchInterval: 10000,
  })

  const handleMutation = useMutation({
    mutationFn: handleIncident,
    onSuccess: () => {
      queryClient.invalidateQueries(['incidents'])
      setSelectedIncident(null)
    },
  })

  const getSeverityBadge = (severity) => {
    const classes = {
      critical: 'badge-red',
      high: 'bg-orange-100 text-orange-800',
      medium: 'badge-yellow',
      low: 'badge-green',
    }
    return <span className={clsx("badge", classes[severity] || 'badge-primary')}>{severity}</span>
  }

  const columns = [
    {
      key: 'severity',
      header: 'Severity',
      render: (value) => getSeverityBadge(value),
    },
    { key: 'title', header: 'Title' },
    { key: 'product', header: 'Product' },
    {
      key: 'status',
      header: 'Status',
      render: (value) => (
        <span className={clsx(
          "badge",
          value === 'open' ? "badge-red" : value === 'investigating' ? "badge-yellow" : "badge-green"
        )}>
          {value}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (value) => new Date(value).toLocaleString(),
    },
    {
      key: 'actions',
      header: '',
      render: (_, row) => row.status !== 'resolved' && (
        <button
          onClick={() => setSelectedIncident(row)}
          className="btn btn-sm btn-secondary"
        >
          <Zap className="w-3 h-3 mr-1" />
          Handle
        </button>
      ),
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
        Failed to load incidents: {error.message}
      </div>
    )
  }

  const openIncidents = incidents?.filter(i => i.status === 'open') || []
  const investigatingIncidents = incidents?.filter(i => i.status === 'investigating') || []
  const resolvedIncidents = incidents?.filter(i => i.status === 'resolved') || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Incidents</h1>
        <p className="text-gray-500">Monitor and respond to data quality incidents</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card border-l-4 border-l-red-500">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <div>
              <p className="text-sm text-gray-500">Open</p>
              <p className="text-xl font-bold text-gray-900">{openIncidents.length}</p>
            </div>
          </div>
        </div>
        <div className="card border-l-4 border-l-yellow-500">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-yellow-500" />
            <div>
              <p className="text-sm text-gray-500">Investigating</p>
              <p className="text-xl font-bold text-gray-900">{investigatingIncidents.length}</p>
            </div>
          </div>
        </div>
        <div className="card border-l-4 border-l-green-500">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <div>
              <p className="text-sm text-gray-500">Resolved</p>
              <p className="text-xl font-bold text-gray-900">{resolvedIncidents.length}</p>
            </div>
          </div>
        </div>
      </div>

      <DataTable
        data={incidents || []}
        columns={columns}
        emptyMessage="No incidents found"
      />

      {selectedIncident && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Handle Incident
            </h3>
            <p className="text-gray-600 mb-4">
              Use AI agent to automatically handle incident: <strong>{selectedIncident.title}</strong>
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setSelectedIncident(null)}
                className="btn btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={() => handleMutation.mutate(selectedIncident.id)}
                disabled={handleMutation.isLoading}
                className="btn btn-primary flex-1"
              >
                {handleMutation.isLoading ? 'Processing...' : 'Run AI Agent'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
