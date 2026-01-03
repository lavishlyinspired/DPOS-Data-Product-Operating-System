import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getProducts, getLineage, getImpact } from '../api/client'
import { GitBranch, ArrowRight, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

export default function Lineage() {
  const [selectedProduct, setSelectedProduct] = useState(null)

  const { data: products } = useQuery({
    queryKey: ['products'],
    queryFn: getProducts,
  })

  const { data: lineage, isLoading: loadingLineage } = useQuery({
    queryKey: ['lineage', selectedProduct],
    queryFn: () => getLineage(selectedProduct),
    enabled: !!selectedProduct,
  })

  const { data: impact } = useQuery({
    queryKey: ['impact', selectedProduct],
    queryFn: () => getImpact(selectedProduct),
    enabled: !!selectedProduct,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Lineage</h1>
        <p className="text-gray-500">Trace data flow and understand dependencies</p>
      </div>

      <div className="card">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select a data product to view its lineage
        </label>
        <select
          value={selectedProduct || ''}
          onChange={(e) => setSelectedProduct(e.target.value || null)}
          className="input max-w-md"
        >
          <option value="">Choose a product...</option>
          {products?.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {selectedProduct && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Upstream */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-primary-600" />
              Upstream Sources
            </h3>
            {loadingLineage ? (
              <div className="animate-pulse space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-12 bg-gray-100 rounded" />
                ))}
              </div>
            ) : lineage?.upstream?.length > 0 ? (
              <ul className="space-y-2">
                {lineage.upstream.map((item, idx) => (
                  <li
                    key={idx}
                    className="p-3 bg-gray-50 rounded-lg flex items-center justify-between"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{item.name}</p>
                      <p className="text-sm text-gray-500">{item.type}</p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 text-sm">No upstream sources</p>
            )}
          </div>

          {/* Current Product */}
          <div className="card bg-primary-50 border-primary-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Selected Product
            </h3>
            <div className="p-4 bg-white rounded-lg border border-primary-200">
              <p className="font-semibold text-gray-900">
                {products?.find(p => p.id === selectedProduct)?.name}
              </p>
              <p className="text-sm text-gray-500 mt-1">
                {products?.find(p => p.id === selectedProduct)?.domain}
              </p>
            </div>

            {impact && (
              <div className="mt-4">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Impact Analysis</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Affected Products</span>
                    <span className="font-medium">{impact.affected_count || 0}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Risk Level</span>
                    <span className={clsx(
                      "badge",
                      impact.risk === 'high' ? "badge-red" : impact.risk === 'medium' ? "badge-yellow" : "badge-green"
                    )}>
                      {impact.risk || 'low'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Downstream */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-primary-600 rotate-180" />
              Downstream Consumers
            </h3>
            {loadingLineage ? (
              <div className="animate-pulse space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-12 bg-gray-100 rounded" />
                ))}
              </div>
            ) : lineage?.downstream?.length > 0 ? (
              <ul className="space-y-2">
                {lineage.downstream.map((item, idx) => (
                  <li
                    key={idx}
                    className="p-3 bg-gray-50 rounded-lg flex items-center justify-between"
                  >
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                    <div className="text-right">
                      <p className="font-medium text-gray-900">{item.name}</p>
                      <p className="text-sm text-gray-500">{item.type}</p>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-500 text-sm">No downstream consumers</p>
            )}
          </div>
        </div>
      )}

      {!selectedProduct && (
        <div className="card text-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Select a Product</h3>
          <p className="text-gray-500 mt-1">
            Choose a data product above to view its lineage and dependencies
          </p>
        </div>
      )}
    </div>
  )
}
