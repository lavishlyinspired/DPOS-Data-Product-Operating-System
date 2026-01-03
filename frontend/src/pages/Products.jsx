import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getProducts } from '../api/client'
import DataTable from '../components/DataTable'
import { Database, ExternalLink } from 'lucide-react'
import clsx from 'clsx'

export default function Products() {
  const { data: products, isLoading, error } = useQuery({
    queryKey: ['products'],
    queryFn: getProducts,
  })

  const columns = [
    {
      key: 'name',
      header: 'Product Name',
      render: (value, row) => (
        <Link to={`/products/${row.id}`} className="text-primary-600 hover:text-primary-800 font-medium">
          {value}
        </Link>
      ),
    },
    { key: 'domain', header: 'Domain' },
    { key: 'owner', header: 'Owner' },
    {
      key: 'health_score',
      header: 'Health',
      render: (value) => (
        <div className="flex items-center gap-2">
          <div className="w-16 bg-gray-200 rounded-full h-2">
            <div
              className={clsx(
                "h-2 rounded-full",
                value >= 80 ? "bg-green-500" : value >= 60 ? "bg-yellow-500" : "bg-red-500"
              )}
              style={{ width: `${value}%` }}
            />
          </div>
          <span className="text-sm text-gray-600">{value}%</span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (value) => (
        <span className={clsx(
          "badge",
          value === 'active' ? "badge-green" : value === 'deprecated' ? "badge-red" : "badge-yellow"
        )}>
          {value}
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (_, row) => (
        <Link to={`/products/${row.id}`} className="text-gray-400 hover:text-gray-600">
          <ExternalLink className="w-4 h-4" />
        </Link>
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
        Failed to load products: {error.message}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Data Products</h1>
          <p className="text-gray-500">Manage your data products catalog</p>
        </div>
        <button className="btn btn-primary">
          <Database className="w-4 h-4 mr-2" />
          Add Product
        </button>
      </div>

      <DataTable
        data={products || []}
        columns={columns}
        emptyMessage="No data products found"
      />
    </div>
  )
}
