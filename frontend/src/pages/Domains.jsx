import { useQuery } from '@tanstack/react-query'
import { getDomains } from '../api/client'
import { FolderTree, Database } from 'lucide-react'
import clsx from 'clsx'

export default function Domains() {
  const { data: domains, isLoading, error } = useQuery({
    queryKey: ['domains'],
    queryFn: getDomains,
  })

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
        Failed to load domains: {error.message}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Domains</h1>
          <p className="text-gray-500">Organize data products by business domains</p>
        </div>
        <button className="btn btn-primary">
          <FolderTree className="w-4 h-4 mr-2" />
          Add Domain
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {domains?.map((domain) => (
          <div key={domain.id} className="card hover:shadow-lg transition-shadow cursor-pointer">
            <div className="flex items-start justify-between">
              <div className={clsx(
                "p-3 rounded-lg",
                domain.color ? `bg-${domain.color}-50` : "bg-primary-50"
              )}>
                <FolderTree className={clsx(
                  "w-6 h-6",
                  domain.color ? `text-${domain.color}-600` : "text-primary-600"
                )} />
              </div>
              <span className="badge badge-primary">{domain.product_count || 0} products</span>
            </div>
            <h3 className="mt-4 text-lg font-semibold text-gray-900">{domain.name}</h3>
            <p className="mt-1 text-sm text-gray-500">{domain.description}</p>
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Owner</span>
                <span className="font-medium text-gray-900">{domain.owner}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {(!domains || domains.length === 0) && (
        <div className="text-center py-12">
          <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No domains found</h3>
          <p className="text-gray-500 mt-1">Get started by creating your first data domain</p>
        </div>
      )}
    </div>
  )
}
