import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getProducts, ingestCSV, ingestJSON, ingestRecords } from '../api/client'
import { Upload, FileText, Check, X, AlertTriangle, FileJson, Table } from 'lucide-react'
import clsx from 'clsx'

export default function Ingestion() {
  const [selectedProduct, setSelectedProduct] = useState('')
  const [validateOnUpload, setValidateOnUpload] = useState(true)
  const [uploadResult, setUploadResult] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [jsonInput, setJsonInput] = useState('')
  const [activeTab, setActiveTab] = useState('file') // file, json, paste

  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ['products'],
    queryFn: () => getProducts(),
  })

  const uploadMutation = useMutation({
    mutationFn: async ({ file, type }) => {
      if (type === 'csv') {
        return await ingestCSV(selectedProduct, file, validateOnUpload)
      } else {
        return await ingestJSON(selectedProduct, file, validateOnUpload)
      }
    },
    onSuccess: (data) => {
      setUploadResult(data)
    },
    onError: (error) => {
      setUploadResult({ error: error.message })
    }
  })

  const jsonMutation = useMutation({
    mutationFn: async (records) => {
      return await ingestRecords(selectedProduct, records, validateOnUpload)
    },
    onSuccess: (data) => {
      setUploadResult(data)
    },
    onError: (error) => {
      setUploadResult({ error: error.message })
    }
  })

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (!selectedProduct) {
      alert('Please select a product first')
      return
    }

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFile = (file) => {
    const type = file.name.endsWith('.csv') ? 'csv' : 'json'
    uploadMutation.mutate({ file, type })
  }

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleJsonSubmit = () => {
    if (!selectedProduct) {
      alert('Please select a product first')
      return
    }

    try {
      const records = JSON.parse(jsonInput)
      const data = Array.isArray(records) ? records : [records]
      jsonMutation.mutate(data)
    } catch (e) {
      setUploadResult({ error: 'Invalid JSON format' })
    }
  }

  const clearResult = () => {
    setUploadResult(null)
    setJsonInput('')
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Ingestion</h1>
        <p className="text-gray-500">Upload and validate data against product contracts</p>
      </div>

      {/* Configuration */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Product
            </label>
            <select
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            >
              <option value="">Select a product...</option>
              {products?.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name} ({product.id})
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={validateOnUpload}
                onChange={(e) => setValidateOnUpload(e.target.checked)}
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <span className="text-sm font-medium text-gray-700">
                Validate against contract on upload
              </span>
            </label>
          </div>
        </div>
      </div>

      {/* Upload Tabs */}
      <div className="card">
        <div className="flex border-b border-gray-200 mb-4">
          <button
            onClick={() => setActiveTab('file')}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px",
              activeTab === 'file'
                ? "border-primary-500 text-primary-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            <div className="flex items-center gap-2">
              <Upload className="w-4 h-4" />
              File Upload
            </div>
          </button>
          <button
            onClick={() => setActiveTab('json')}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px",
              activeTab === 'json'
                ? "border-primary-500 text-primary-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            )}
          >
            <div className="flex items-center gap-2">
              <FileJson className="w-4 h-4" />
              JSON Input
            </div>
          </button>
        </div>

        {activeTab === 'file' && (
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={clsx(
              "border-2 border-dashed rounded-lg p-8 text-center transition-colors",
              dragActive ? "border-primary-500 bg-primary-50" : "border-gray-300",
              !selectedProduct && "opacity-50 cursor-not-allowed"
            )}
          >
            <Upload className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-700 mb-2">
              Drag and drop your file here
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Supports CSV and JSON files
            </p>
            <label className={clsx(
              "btn btn-primary cursor-pointer",
              !selectedProduct && "opacity-50 cursor-not-allowed"
            )}>
              <input
                type="file"
                accept=".csv,.json"
                onChange={handleFileInput}
                disabled={!selectedProduct}
                className="hidden"
              />
              Browse Files
            </label>
          </div>
        )}

        {activeTab === 'json' && (
          <div>
            <textarea
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              placeholder='Paste JSON data here...
Example:
[
  {"name": "Product 1", "price": 100},
  {"name": "Product 2", "price": 200}
]'
              className="w-full h-64 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={clearResult}
                className="btn btn-secondary"
              >
                Clear
              </button>
              <button
                onClick={handleJsonSubmit}
                disabled={!selectedProduct || !jsonInput}
                className={clsx(
                  "btn btn-primary",
                  (!selectedProduct || !jsonInput) && "opacity-50 cursor-not-allowed"
                )}
              >
                Submit JSON
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {(uploadMutation.isPending || jsonMutation.isPending) && (
        <div className="card">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <span className="ml-3 text-gray-600">Processing data...</span>
          </div>
        </div>
      )}

      {/* Results */}
      {uploadResult && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Ingestion Results</h3>
            <button onClick={clearResult} className="text-gray-400 hover:text-gray-600">
              <X className="w-5 h-5" />
            </button>
          </div>

          {uploadResult.error ? (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center gap-3">
              <AlertTriangle className="w-5 h-5" />
              <span>{uploadResult.error}</span>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Summary Stats */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-gray-900">
                    {uploadResult.records_received}
                  </div>
                  <div className="text-sm text-gray-500">Records Received</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {uploadResult.records_valid}
                  </div>
                  <div className="text-sm text-green-600">Valid Records</div>
                </div>
                <div className="bg-red-50 p-4 rounded-lg text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {uploadResult.records_invalid}
                  </div>
                  <div className="text-sm text-red-600">Invalid Records</div>
                </div>
                <div className={clsx(
                  "p-4 rounded-lg text-center",
                  uploadResult.records_invalid === 0 ? "bg-green-50" : "bg-yellow-50"
                )}>
                  <div className={clsx(
                    "text-2xl font-bold",
                    uploadResult.records_invalid === 0 ? "text-green-600" : "text-yellow-600"
                  )}>
                    {uploadResult.records_invalid === 0 ? (
                      <Check className="w-8 h-8 mx-auto" />
                    ) : (
                      <AlertTriangle className="w-8 h-8 mx-auto" />
                    )}
                  </div>
                  <div className={clsx(
                    "text-sm",
                    uploadResult.records_invalid === 0 ? "text-green-600" : "text-yellow-600"
                  )}>
                    {uploadResult.records_invalid === 0 ? 'All Valid' : 'Has Errors'}
                  </div>
                </div>
              </div>

              {/* Validation Errors */}
              {uploadResult.validation_errors?.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Validation Errors</h4>
                  <div className="bg-red-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                    <ul className="space-y-2">
                      {uploadResult.validation_errors.slice(0, 20).map((error, idx) => (
                        <li key={idx} className="text-sm text-red-700 flex items-start gap-2">
                          <X className="w-4 h-4 mt-0.5 flex-shrink-0" />
                          <span>
                            {typeof error === 'string' ? error : JSON.stringify(error)}
                          </span>
                        </li>
                      ))}
                      {uploadResult.validation_errors.length > 20 && (
                        <li className="text-sm text-red-600 font-medium">
                          ... and {uploadResult.validation_errors.length - 20} more errors
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              )}

              {/* Success Message */}
              {uploadResult.records_invalid === 0 && (
                <div className="bg-green-50 text-green-700 p-4 rounded-lg flex items-center gap-3">
                  <Check className="w-5 h-5" />
                  <span>
                    All {uploadResult.records_valid} records passed validation and are ready for processing!
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Sample Data Format */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Supported Formats</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Table className="w-5 h-5 text-green-600" />
              <span className="font-medium text-gray-900">CSV Format</span>
            </div>
            <pre className="bg-gray-50 p-4 rounded-lg text-sm overflow-x-auto">
{`id,name,price,category
1,Widget A,29.99,electronics
2,Widget B,49.99,electronics
3,Gadget C,99.99,gadgets`}
            </pre>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileJson className="w-5 h-5 text-blue-600" />
              <span className="font-medium text-gray-900">JSON Format</span>
            </div>
            <pre className="bg-gray-50 p-4 rounded-lg text-sm overflow-x-auto">
{`[
  {"id": 1, "name": "Widget A", "price": 29.99},
  {"id": 2, "name": "Widget B", "price": 49.99}
]`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}
