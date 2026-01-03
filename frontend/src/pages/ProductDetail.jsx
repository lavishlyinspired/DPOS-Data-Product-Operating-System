import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getProduct, getProductHealth, getLineage } from '../api/client'
import { ArrowLeft, Activity, GitBranch, FileCheck, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

export default function ProductDetail() {
  const { id } = useParams()

  const { data: product, isLoading: loadingProduct } = useQuery({
    queryKey: ['product', id],
    queryFn: () => getProduct(id),
  })

  const { data: health } = useQuery({
    queryKey: ['productHealth', id],
    queryFn: () => getProductHealth(id),
    enabled: !!product,
  })

  const { data: lineage } = useQuery({
    queryKey: ['lineage', id],
    queryFn: () => getLineage(id),
    enabled: !!product,
  })

  if (loadingProduct) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="bg-red-50 text-red-700 p-4 rounded-lg">
        Product not found
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/products" className="p-2 hover:bg-gray-100 rounded-lg">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{product.name}</h1>
          <p className="text-gray-500">{product.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-gray-900">Health Score</h3>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {health?.score || product.health_score || 0}%
          </div>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div
              className={clsx(
                "h-2 rounded-full",
                (health?.score || 0) >= 80 ? "bg-green-500" : (health?.score || 0) >= 60 ? "bg-yellow-500" : "bg-red-500"
              )}
              style={{ width: `${health?.score || product.health_score || 0}%` }}
            />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <FileCheck className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold text-gray-900">Contracts</h3>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {product.contracts?.length || 0}
          </div>
          <p className="text-sm text-gray-500 mt-1">Active data contracts</p>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <h3 className="font-semibold text-gray-900">Issues</h3>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {health?.issues?.length || 0}
          </div>
          <p className="text-sm text-gray-500 mt-1">Open quality issues</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Product Details</h3>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-gray-500">Domain</dt>
              <dd className="font-medium text-gray-900">{product.domain}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Owner</dt>
              <dd className="font-medium text-gray-900">{product.owner}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Status</dt>
              <dd>
                <span className={clsx(
                  "badge",
                  product.status === 'active' ? "badge-green" : "badge-yellow"
                )}>
                  {product.status}
                </span>
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Created</dt>
              <dd className="font-medium text-gray-900">{product.created_at}</dd>
            </div>
          </dl>
        </div>

        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            <GitBranch className="w-5 h-5 text-primary-600" />
            <h3 className="text-lg font-semibold text-gray-900">Lineage</h3>
          </div>
          {lineage?.upstream?.length > 0 || lineage?.downstream?.length > 0 ? (
            <div className="space-y-4">
              {lineage.upstream?.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-2">Upstream</h4>
                  <ul className="space-y-1">
                    {lineage.upstream.map((item, idx) => (
                      <li key={idx} className="text-sm text-gray-900">{item.name}</li>
                    ))}
                  </ul>
                </div>
              )}
              {lineage.downstream?.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-2">Downstream</h4>
                  <ul className="space-y-1">
                    {lineage.downstream.map((item, idx) => (
                      <li key={idx} className="text-sm text-gray-900">{item.name}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="text-gray-500 text-sm">No lineage data available</p>
          )}
        </div>
      </div>
    </div>
  )
}
