import { useQuery } from '@tanstack/react-query'
import { getDashboardStats, getHealthByDomain, getHealth } from '../api/client'
import StatCard from '../components/StatCard'
import { Database, FileCheck, AlertTriangle, Activity, FolderTree, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'

export default function Dashboard() {
  const [refreshing, setRefreshing] = useState(false)

  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: getDashboardStats,
    refetchInterval: 30000,
  })

  const { data: healthByDomain } = useQuery({
    queryKey: ['healthByDomain'],
    queryFn: getHealthByDomain,
    refetchInterval: 60000,
  })

  const { data: systemHealth } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: getHealth,
    refetchInterval: 60000,
  })

  const handleRefresh = async () => {
    setRefreshing(true)
    await refetch()
    setRefreshing(false)
  }

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
        Failed to load dashboard stats: {error.message}
      </div>
    )
  }

  const healthScore = stats?.avg_health_score || 0
  const healthColor = healthScore >= 80 ? 'green' : healthScore >= 60 ? 'yellow' : 'red'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Overview of your Data Product Operating System</p>
        </div>
        <button
          onClick={handleRefresh}
          className={clsx(
            "btn btn-secondary flex items-center gap-2",
            refreshing && "opacity-50 cursor-not-allowed"
          )}
          disabled={refreshing}
        >
          <RefreshCw className={clsx("w-4 h-4", refreshing && "animate-spin")} />
          Refresh
        </button>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Products"
          value={stats?.total_products || 0}
          icon={Database}
          color="primary"
          subtitle={`${stats?.healthy_products || 0} healthy, ${stats?.degraded_products || 0} degraded`}
        />
        <StatCard
          title="Domains"
          value={stats?.total_domains || 0}
          icon={FolderTree}
          color="blue"
        />
        <StatCard
          title="Active Contracts"
          value={stats?.active_contracts || 0}
          icon={FileCheck}
          color="green"
        />
        <StatCard
          title="Open Incidents"
          value={stats?.open_incidents || 0}
          icon={AlertTriangle}
          color={stats?.open_incidents > 0 ? 'red' : 'green'}
          subtitle={stats?.critical_incidents > 0 ? `${stats.critical_incidents} critical` : null}
        />
      </div>

      {/* Health Score Card */}
      <div className="card bg-gradient-to-r from-gray-50 to-gray-100">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Overall Health Score</h3>
            <p className="text-sm text-gray-500">Based on incidents and contract compliance</p>
          </div>
          <div className="flex items-center gap-4">
            <div className={clsx(
              "text-5xl font-bold",
              healthColor === 'green' && "text-green-600",
              healthColor === 'yellow' && "text-yellow-600",
              healthColor === 'red' && "text-red-600"
            )}>
              {healthScore}%
            </div>
            <div className={clsx(
              "p-3 rounded-full",
              healthColor === 'green' && "bg-green-100",
              healthColor === 'yellow' && "bg-yellow-100",
              healthColor === 'red' && "bg-red-100"
            )}>
              {healthScore >= 80 ? (
                <TrendingUp className="w-8 h-8 text-green-600" />
              ) : (
                <TrendingDown className={clsx(
                  "w-8 h-8",
                  healthColor === 'yellow' ? "text-yellow-600" : "text-red-600"
                )} />
              )}
            </div>
          </div>
        </div>

        {/* Health Bar */}
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={clsx(
                "h-3 rounded-full transition-all duration-500",
                healthColor === 'green' && "bg-green-500",
                healthColor === 'yellow' && "bg-yellow-500",
                healthColor === 'red' && "bg-red-500"
              )}
              style={{ width: `${healthScore}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Health by Domain */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Health by Domain</h3>
          {healthByDomain?.length > 0 ? (
            <div className="space-y-3">
              {healthByDomain.map((domain) => (
                <div key={domain.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                  <div>
                    <div className="font-medium text-gray-900">{domain.name}</div>
                    <div className="text-sm text-gray-500">{domain.product_count} products</div>
                  </div>
                  <div className="flex items-center gap-3">
                    {domain.open_incidents > 0 && (
                      <span className="text-sm text-red-600">{domain.open_incidents} incidents</span>
                    )}
                    <span className={clsx(
                      "badge",
                      domain.health === 'healthy' ? "badge-green" : "badge-red"
                    )}>
                      {domain.health}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No domains found</p>
          )}
        </div>

        {/* Recent Activity */}
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Incidents</h3>
          {stats?.recent_activity?.length > 0 ? (
            <div className="space-y-3">
              {stats.recent_activity.slice(0, 5).map((activity, idx) => (
                <div key={idx} className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded-lg">
                  <span className={clsx(
                    "w-2 h-2 rounded-full",
                    activity.severity === 'critical' && "bg-red-500",
                    activity.severity === 'high' && "bg-orange-500",
                    activity.severity === 'medium' && "bg-yellow-500",
                    activity.severity === 'low' && "bg-blue-500"
                  )}></span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-900 truncate">
                      {activity.type} - {activity.product_name}
                    </div>
                    <div className="text-xs text-gray-500">{activity.id}</div>
                  </div>
                  <span className={clsx(
                    "badge text-xs",
                    activity.status === 'open' ? "badge-red" : "badge-green"
                  )}>
                    {activity.status}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No recent incidents</p>
          )}
        </div>
      </div>

      {/* System Status */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">System Status</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={clsx(
                "w-3 h-3 rounded-full",
                systemHealth?.api === 'healthy' ? "bg-green-500" : "bg-red-500"
              )}></div>
              <span className="text-sm font-medium text-gray-700">API Server</span>
            </div>
            <span className={clsx(
              "badge",
              systemHealth?.api === 'healthy' ? "badge-green" : "badge-red"
            )}>
              {systemHealth?.api || 'Unknown'}
            </span>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={clsx(
                "w-3 h-3 rounded-full",
                systemHealth?.database === 'healthy' ? "bg-green-500" : "bg-red-500"
              )}></div>
              <span className="text-sm font-medium text-gray-700">Neo4j Database</span>
            </div>
            <span className={clsx(
              "badge",
              systemHealth?.database === 'healthy' ? "badge-green" : "badge-red"
            )}>
              {systemHealth?.database?.split(':')[0] || 'Unknown'}
            </span>
          </div>

          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-sm font-medium text-gray-700">AI Agents</span>
            </div>
            <span className="badge badge-green">Active</span>
          </div>
        </div>
      </div>
    </div>
  )
}
