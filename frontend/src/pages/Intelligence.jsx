import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { intelligenceQuery, intelligenceCypher, intelligenceInsights } from '../api/client'
import { Brain, Search, Code, Lightbulb, Send, Loader2, Copy, Check } from 'lucide-react'
import clsx from 'clsx'

export default function Intelligence() {
  const [activeTab, setActiveTab] = useState('query')
  const [input, setInput] = useState('')
  const [results, setResults] = useState([])
  const [copied, setCopied] = useState(false)

  const { data: insights, isLoading: loadingInsights } = useQuery({
    queryKey: ['insights'],
    queryFn: intelligenceInsights,
    refetchInterval: 60000,
  })

  const queryMutation = useMutation({
    mutationFn: intelligenceQuery,
    onSuccess: (data) => {
      setResults(prev => [{
        type: 'query',
        question: input,
        ...data,
        timestamp: new Date().toISOString()
      }, ...prev])
      setInput('')
    },
  })

  const cypherMutation = useMutation({
    mutationFn: intelligenceCypher,
    onSuccess: (data) => {
      setResults(prev => [{
        type: 'cypher',
        question: input,
        ...data,
        timestamp: new Date().toISOString()
      }, ...prev])
      setInput('')
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim()) return

    if (activeTab === 'query') {
      queryMutation.mutate(input)
    } else {
      cypherMutation.mutate(input)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isLoading = queryMutation.isLoading || cypherMutation.isLoading

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Brain className="w-7 h-7 text-primary-600" />
          Intelligence
        </h1>
        <p className="text-gray-500">Natural language queries powered by Graph RAG</p>
      </div>

      {/* Insights Panel */}
      {insights && !loadingInsights && (
        <div className="card bg-gradient-to-r from-primary-50 to-blue-50 border-primary-100">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="w-5 h-5 text-primary-600" />
            <h3 className="font-semibold text-gray-900">Automated Insights</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white rounded-lg p-3 shadow-sm">
              <p className="text-sm text-gray-500">Total Products</p>
              <p className="text-2xl font-bold text-gray-900">
                {insights.health_summary?.total_products || 0}
              </p>
            </div>
            <div className="bg-white rounded-lg p-3 shadow-sm">
              <p className="text-sm text-gray-500">Healthy</p>
              <p className="text-2xl font-bold text-green-600">
                {insights.health_summary?.healthy || 0}
              </p>
            </div>
            <div className="bg-white rounded-lg p-3 shadow-sm">
              <p className="text-sm text-gray-500">Degraded</p>
              <p className="text-2xl font-bold text-red-600">
                {insights.health_summary?.degraded || 0}
              </p>
            </div>
          </div>
          {insights.recommendations?.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-sm font-medium text-gray-700">Recommendations:</p>
              {insights.recommendations.map((rec, idx) => (
                <div
                  key={idx}
                  className={clsx(
                    "text-sm p-2 rounded",
                    rec.priority === 'high' ? "bg-red-100 text-red-800" :
                    rec.priority === 'medium' ? "bg-yellow-100 text-yellow-800" :
                    "bg-blue-100 text-blue-800"
                  )}
                >
                  {rec.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab Selection */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('query')}
          className={clsx(
            "px-4 py-2 rounded-lg flex items-center gap-2 transition-colors",
            activeTab === 'query'
              ? "bg-primary-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          )}
        >
          <Search className="w-4 h-4" />
          Natural Language
        </button>
        <button
          onClick={() => setActiveTab('cypher')}
          className={clsx(
            "px-4 py-2 rounded-lg flex items-center gap-2 transition-colors",
            activeTab === 'cypher'
              ? "bg-primary-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          )}
        >
          <Code className="w-4 h-4" />
          Cypher Generation
        </button>
      </div>

      {/* Query Input */}
      <form onSubmit={handleSubmit} className="card">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {activeTab === 'query'
            ? 'Ask a question about your data products'
            : 'Describe the query you want to generate'}
        </label>
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              activeTab === 'query'
                ? 'e.g., How many products have open incidents?'
                : 'e.g., List all products in the Customer domain'
            }
            className="input flex-1"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="btn btn-primary"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Ask
              </>
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {activeTab === 'query'
            ? 'Uses hybrid retrieval (semantic + graph + keyword) for best results'
            : 'Generates and executes Cypher queries against the knowledge graph'}
        </p>
      </form>

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">Results</h3>
          {results.map((result, idx) => (
            <div key={idx} className="card">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <span className={clsx(
                    "badge",
                    result.type === 'query' ? "badge-primary" : "badge-green"
                  )}>
                    {result.type === 'query' ? 'Natural Language' : 'Cypher'}
                  </span>
                  <span className="text-sm text-gray-500 ml-2">
                    {new Date(result.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {result.confidence && (
                  <span className="text-sm text-gray-500">
                    Confidence: {Math.round(result.confidence * 100)}%
                  </span>
                )}
              </div>

              <p className="font-medium text-gray-900 mb-3">Q: {result.question}</p>

              {/* Answer */}
              <div className="bg-gray-50 rounded-lg p-4 mb-3">
                <p className="text-gray-800 whitespace-pre-wrap">{result.answer}</p>
              </div>

              {/* Generated Cypher */}
              {result.generated_cypher && (
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">Generated Cypher:</span>
                    <button
                      onClick={() => copyToClipboard(result.generated_cypher)}
                      className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          Copy
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg text-sm overflow-x-auto">
                    {result.generated_cypher}
                  </pre>
                </div>
              )}

              {/* Sources */}
              {result.sources?.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-gray-700">Sources:</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {result.sources.map((source, sidx) => (
                      <span key={sidx} className="badge badge-primary">
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Query Results (for Cypher) */}
              {result.results?.length > 0 && (
                <div className="mt-3">
                  <span className="text-sm font-medium text-gray-700">
                    Query Results ({result.results.length}):
                  </span>
                  <div className="mt-2 max-h-48 overflow-y-auto">
                    <pre className="text-xs bg-gray-100 p-2 rounded">
                      {JSON.stringify(result.results.slice(0, 10), null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Example Queries */}
      {results.length === 0 && (
        <div className="card">
          <h3 className="font-semibold text-gray-900 mb-3">Example Queries</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              "How many data products are there?",
              "List products with open incidents",
              "What is the lineage for customer data?",
              "Which products have contract violations?",
              "Show products in the Order domain",
              "Who owns the inventory product?"
            ].map((example, idx) => (
              <button
                key={idx}
                onClick={() => setInput(example)}
                className="text-left p-3 bg-gray-50 hover:bg-gray-100 rounded-lg text-sm text-gray-700 transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
