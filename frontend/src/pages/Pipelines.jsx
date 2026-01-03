import { useQuery } from '@tanstack/react-query'
import { getPipelines } from '../api/client'
import DataTable from '../components/DataTable'
import { Workflow, Play, Pause, CheckCircle, XCircle } from 'lucide-react'
import clsx from 'clsx'

export default function Pipelines() {
  const { data: pipelines, isLoading, error } = useQuery({
    queryKey: ['pipelines'],
    queryFn: getPipelines,
    refetchInterval: 15000,
  })

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <Play className="w-4 h-4 text-green-500" />
      case 'paused':
        return <Pause className="w-4 h-4 text-yellow-500" />
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />
      default:
        return null
    }
  }

  const columns = [
    {
      key: 'name',
      header: 'Pipeline Name',
      render: (value) => (
        <span className="font-medium text-gray-900">{value}</span>
      ),
    },
    { key: 'source', header: 'Source' },
    { key: 'destination', header: 'Destination' },
    {
      key: 'status',
      header: 'Status',
      render: (value) => (
        <div className="flex items-center gap-2">
          {getStatusIcon(value)}
          <span className={clsx(
            "capitalize",
            value === 'running' ? "text-green-600" :
            value === 'failed' ? "text-red-600" :
            value === 'paused' ? "text-yellow-600" : "text-gray-600"
          )}>
            {value}
          </span>
        </div>
      ),
    },
    {
      key: 'last_run',
      header: 'Last Run',
      render: (value) => value ? new Date(value).toLocaleString() : 'Never',
    },
    {
      key: 'success_rate',
      header: 'Success Rate',
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
    { key: 'schedule', header: 'Schedule' },
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
        Failed to load pipelines: {error.message}
      </div>
    )
  }

  const runningPipelines = pipelines?.filter(p => p.status === 'running') || []
  const failedPipelines = pipelines?.filter(p => p.status === 'failed') || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Pipelines</h1>
          <p className="text-gray-500">Monitor and manage data ingestion pipelines</p>
        </div>
        <button className="btn btn-primary">
          <Workflow className="w-4 h-4 mr-2" />
          New Pipeline
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card">
          <p className="text-sm text-gray-500">Total Pipelines</p>
          <p className="text-2xl font-bold text-gray-900">{pipelines?.length || 0}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Running</p>
          <p className="text-2xl font-bold text-green-600">{runningPipelines.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Failed</p>
          <p className="text-2xl font-bold text-red-600">{failedPipelines.length}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-500">Avg Success Rate</p>
          <p className="text-2xl font-bold text-gray-900">
            {pipelines?.length > 0
              ? Math.round(pipelines.reduce((acc, p) => acc + (p.success_rate || 0), 0) / pipelines.length)
              : 0}%
          </p>
        </div>
      </div>

      <DataTable
        data={pipelines || []}
        columns={columns}
        emptyMessage="No pipelines configured"
      />
    </div>
  )
}
