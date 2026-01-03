import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { searchMarketplace } from '../api/client'
import { Search, Database, Star, Download } from 'lucide-react'
import clsx from 'clsx'

export default function Marketplace() {
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  const { data: results, isLoading, isFetching } = useQuery({
    queryKey: ['marketplace', debouncedQuery],
    queryFn: () => searchMarketplace(debouncedQuery),
    enabled: debouncedQuery.length > 0,
  })

  const handleSearch = (e) => {
    e.preventDefault()
    setDebouncedQuery(searchQuery)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Marketplace</h1>
        <p className="text-gray-500">Discover and subscribe to data products</p>
      </div>

      <form onSubmit={handleSearch} className="card">
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for data products..."
              className="input pl-10 w-full"
            />
          </div>
          <button type="submit" className="btn btn-primary">
            Search
          </button>
        </div>
      </form>

      {isLoading || isFetching ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : results?.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {results.map((product) => (
            <div key={product.id} className="card hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between">
                <div className="p-2 bg-primary-50 rounded-lg">
                  <Database className="w-5 h-5 text-primary-600" />
                </div>
                <div className="flex items-center gap-1 text-yellow-500">
                  <Star className="w-4 h-4 fill-current" />
                  <span className="text-sm text-gray-600">{product.rating || 0}</span>
                </div>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">{product.name}</h3>
              <p className="mt-1 text-sm text-gray-500 line-clamp-2">{product.description}</p>

              <div className="mt-4 flex flex-wrap gap-2">
                {product.tags?.map((tag, idx) => (
                  <span key={idx} className="badge badge-primary">{tag}</span>
                ))}
              </div>

              <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
                <div className="text-sm">
                  <span className="text-gray-500">by </span>
                  <span className="font-medium text-gray-900">{product.owner}</span>
                </div>
                <button className="btn btn-sm btn-secondary">
                  <Download className="w-3 h-3 mr-1" />
                  Subscribe
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : debouncedQuery ? (
        <div className="card text-center py-12">
          <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">No results found</h3>
          <p className="text-gray-500 mt-1">
            Try adjusting your search terms or browse all products
          </p>
        </div>
      ) : (
        <div className="card text-center py-12">
          <Search className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Search the Marketplace</h3>
          <p className="text-gray-500 mt-1">
            Enter a search term to find data products
          </p>
        </div>
      )}
    </div>
  )
}
