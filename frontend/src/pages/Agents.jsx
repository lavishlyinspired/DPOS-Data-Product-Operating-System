import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  runDiscoveryAgent, runQAAgent, runImpactAgent, runHealingAgent,
  runStewardAgent, runPredictiveAgent, runOrchestratorAgent,
  runContractEvolutionAgent, runCrossDomainAgent, runNotificationAgent,
  runSLAMonitorAgent, runInsightsAgent
} from '../api/client'
import {
  Bot, Search, MessageSquare, GitBranch, Send, Loader2,
  Shield, Brain, Network, Layers, Bell, FileText, HeartPulse,
  ChevronDown, ChevronRight, Clock, BarChart3, AlertTriangle
} from 'lucide-react'
import clsx from 'clsx'

const agents = [
  {
    id: 'discovery',
    name: 'Discovery Agent',
    description: 'Discover and catalog data assets across your organization',
    icon: Search,
    color: 'blue',
    inputType: 'text',
    inputLabel: 'Enter discovery query',
    inputPlaceholder: 'e.g., Find all customer-related data products',
    category: 'core'
  },
  {
    id: 'qa',
    name: 'Q&A Agent',
    description: 'Ask questions about your data products using natural language',
    icon: MessageSquare,
    color: 'green',
    inputType: 'text',
    inputLabel: 'Ask a question',
    inputPlaceholder: 'e.g., What is the schema of the orders product?',
    category: 'core'
  },
  {
    id: 'healing',
    name: 'Healing Agent',
    description: 'LLM-powered root cause analysis and automated remediation',
    icon: HeartPulse,
    color: 'red',
    inputType: 'incident',
    inputLabel: 'Incident ID',
    inputPlaceholder: 'e.g., INC_12345',
    features: ['Root cause analysis', 'Severity reassessment', 'Remediation planning', 'Stakeholder narratives'],
    category: 'core'
  },
  {
    id: 'steward',
    name: 'Steward Agent',
    description: 'Intelligent governance recommendations and compliance monitoring',
    icon: Shield,
    color: 'purple',
    inputType: 'incident',
    inputLabel: 'Incident ID',
    inputPlaceholder: 'e.g., INC_12345',
    features: ['Governance recommendations', 'Preventive measures', 'Policy validation'],
    category: 'core'
  },
  {
    id: 'impact',
    name: 'Impact Agent',
    description: 'Analyze downstream effects with LLM-generated risk narratives',
    icon: GitBranch,
    color: 'yellow',
    inputType: 'product',
    inputLabel: 'Product ID',
    inputPlaceholder: 'e.g., customer_orders',
    features: ['Dependency mapping', 'Risk assessment', 'Impact narratives', 'Mitigation suggestions'],
    category: 'core'
  },
  {
    id: 'predictive',
    name: 'Predictive Agent',
    description: 'Predict issues before they occur using historical patterns',
    icon: Brain,
    color: 'indigo',
    inputType: 'products',
    inputLabel: 'Product IDs (comma-separated)',
    inputPlaceholder: 'e.g., orders,inventory,customers',
    features: ['Anomaly detection', 'Risk predictions', 'Preventive actions', 'Trend analysis'],
    category: 'advanced'
  },
  {
    id: 'orchestrator',
    name: 'Orchestrator Agent',
    description: 'Coordinate multiple incidents and agents for efficient resolution',
    icon: Network,
    color: 'cyan',
    inputType: 'incidents',
    inputLabel: 'Incident IDs (comma-separated)',
    inputPlaceholder: 'e.g., INC_001,INC_002,INC_003',
    features: ['Incident correlation', 'Priority management', 'Batch remediation', 'Agent coordination'],
    category: 'advanced'
  },
  {
    id: 'contract',
    name: 'Contract Evolution',
    description: 'Intelligently evolve data contracts based on patterns and feedback',
    icon: FileText,
    color: 'orange',
    inputType: 'contract',
    inputLabel: 'Contract ID',
    inputPlaceholder: 'e.g., CON_orders_quality',
    features: ['Violation analysis', 'Threshold optimization', 'New rule suggestions', 'Evolution planning'],
    category: 'advanced'
  },
  {
    id: 'crossdomain',
    name: 'Cross-Domain Agent',
    description: 'Analyze impacts spanning multiple business domains',
    icon: Layers,
    color: 'teal',
    inputType: 'crossdomain',
    inputLabel: 'Product ID',
    inputPlaceholder: 'e.g., customer_orders',
    features: ['Domain mapping', 'Cascading effects', 'Coordination plans', 'Executive summaries'],
    category: 'advanced'
  },
  {
    id: 'notification',
    name: 'Notification Agent',
    description: 'Create tailored notifications for different stakeholder groups',
    icon: Bell,
    color: 'pink',
    inputType: 'notification',
    inputLabel: 'Product ID',
    inputPlaceholder: 'e.g., customer_orders',
    features: ['Audience targeting', 'Multi-channel delivery', 'Escalation chains', 'Context-aware messaging'],
    category: 'advanced'
  },
  {
    id: 'sla',
    name: 'SLA Monitor Agent',
    description: 'Monitor SLA compliance and detect/predict breaches',
    icon: Clock,
    color: 'amber',
    inputType: 'sla',
    inputLabel: 'Product IDs (optional, comma-separated)',
    inputPlaceholder: 'Leave empty to monitor all, or e.g., orders,inventory',
    features: ['Breach detection', 'Risk prediction', 'Trend analysis', 'Compliance reporting'],
    category: 'advanced'
  },
  {
    id: 'insights',
    name: 'Insights Agent',
    description: 'Generate automated governance insights and executive recommendations',
    icon: BarChart3,
    color: 'emerald',
    inputType: 'insights',
    inputLabel: 'Time Range (days)',
    inputPlaceholder: '30',
    features: ['Executive summaries', 'Health analysis', 'Incident trends', 'Improvement recommendations'],
    category: 'advanced'
  },
]

export default function Agents() {
  const [selectedAgent, setSelectedAgent] = useState(null)
  const [input, setInput] = useState('')
  const [severity, setSeverity] = useState('medium')
  const [eventType, setEventType] = useState('incident')
  const [description, setDescription] = useState('')
  const [results, setResults] = useState([])
  const [showAdvanced, setShowAdvanced] = useState(false)

  const addResult = (agentId, data) => {
    setResults(prev => [{
      agentId,
      timestamp: new Date().toISOString(),
      data,
    }, ...prev])
  }

  const discoveryMutation = useMutation({
    mutationFn: runDiscoveryAgent,
    onSuccess: (data) => addResult('discovery', data),
  })
  const qaMutation = useMutation({
    mutationFn: runQAAgent,
    onSuccess: (data) => addResult('qa', data),
  })
  const impactMutation = useMutation({
    mutationFn: runImpactAgent,
    onSuccess: (data) => addResult('impact', data),
  })
  const healingMutation = useMutation({
    mutationFn: (params) => runHealingAgent(params.id, params.severity),
    onSuccess: (data) => addResult('healing', data),
  })
  const stewardMutation = useMutation({
    mutationFn: (params) => runStewardAgent(params.id, params.severity),
    onSuccess: (data) => addResult('steward', data),
  })
  const predictiveMutation = useMutation({
    mutationFn: runPredictiveAgent,
    onSuccess: (data) => addResult('predictive', data),
  })
  const orchestratorMutation = useMutation({
    mutationFn: runOrchestratorAgent,
    onSuccess: (data) => addResult('orchestrator', data),
  })
  const contractMutation = useMutation({
    mutationFn: runContractEvolutionAgent,
    onSuccess: (data) => addResult('contract', data),
  })
  const crossdomainMutation = useMutation({
    mutationFn: (params) => runCrossDomainAgent(params.eventType, params.product, params.severity, params.description),
    onSuccess: (data) => addResult('crossdomain', data),
  })
  const notificationMutation = useMutation({
    mutationFn: (params) => runNotificationAgent(params.eventType, params.severity, params.product, params.summary, params.details),
    onSuccess: (data) => addResult('notification', data),
  })
  const slaMutation = useMutation({
    mutationFn: (productIds) => runSLAMonitorAgent(productIds),
    onSuccess: (data) => addResult('sla', data),
  })
  const insightsMutation = useMutation({
    mutationFn: (timeRangeDays) => runInsightsAgent(timeRangeDays),
    onSuccess: (data) => addResult('insights', data),
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    const agent = agents.find(a => a.id === selectedAgent)

    // Special handling for agents that don't require input
    if (agent.inputType === 'sla') {
      const productIds = input.trim() ? input.split(',').map(s => s.trim()) : null
      slaMutation.mutate(productIds)
      setInput('')
      return
    }

    if (agent.inputType === 'insights') {
      const days = parseInt(input.trim()) || 30
      insightsMutation.mutate(days)
      setInput('')
      return
    }

    if (!input.trim() || !selectedAgent) return

    switch (agent.inputType) {
      case 'text':
        if (selectedAgent === 'discovery') discoveryMutation.mutate(input)
        else if (selectedAgent === 'qa') qaMutation.mutate(input)
        break
      case 'incident':
        if (selectedAgent === 'healing') healingMutation.mutate({ id: input, severity })
        else if (selectedAgent === 'steward') stewardMutation.mutate({ id: input, severity })
        break
      case 'product':
        impactMutation.mutate(input)
        break
      case 'products':
        predictiveMutation.mutate(input.split(',').map(s => s.trim()))
        break
      case 'incidents':
        orchestratorMutation.mutate(input.split(',').map(s => s.trim()))
        break
      case 'contract':
        contractMutation.mutate(input)
        break
      case 'crossdomain':
        crossdomainMutation.mutate({ eventType, product: input, severity, description })
        break
      case 'notification':
        notificationMutation.mutate({ eventType, severity, product: input, summary: description, details: description })
        break
    }
    setInput('')
    setDescription('')
  }

  const isLoading = discoveryMutation.isPending || qaMutation.isPending ||
    impactMutation.isPending || healingMutation.isPending ||
    stewardMutation.isPending || predictiveMutation.isPending ||
    orchestratorMutation.isPending || contractMutation.isPending ||
    crossdomainMutation.isPending || notificationMutation.isPending ||
    slaMutation.isPending || insightsMutation.isPending

  const getAgentConfig = (id) => agents.find(a => a.id === id)
  const coreAgents = agents.filter(a => a.category === 'core')
  const advancedAgents = agents.filter(a => a.category === 'advanced')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Agents</h1>
        <p className="text-gray-500">Intelligent LLM-powered agents for automated data governance</p>
      </div>

      {/* Core Agents */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-3">Core Agents</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {coreAgents.map((agent) => {
            const Icon = agent.icon
            return (
              <button
                key={agent.id}
                onClick={() => setSelectedAgent(agent.id)}
                className={clsx(
                  "card text-left transition-all p-4",
                  selectedAgent === agent.id
                    ? "ring-2 ring-primary-500 bg-primary-50"
                    : "hover:shadow-lg"
                )}
              >
                <div className="p-2 rounded-lg w-fit bg-gray-100">
                  <Icon className="w-5 h-5 text-gray-700" />
                </div>
                <h3 className="mt-3 font-semibold text-gray-900 text-sm">{agent.name}</h3>
                <p className="mt-1 text-xs text-gray-500 line-clamp-2">{agent.description}</p>
              </button>
            )
          })}
        </div>
      </div>

      {/* Advanced Agents */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-lg font-semibold text-gray-800 mb-3 hover:text-primary-600"
        >
          {showAdvanced ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          <span>Advanced Agents</span>
          <span className="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full">
            {advancedAgents.length} agents
          </span>
        </button>

        {showAdvanced && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {advancedAgents.map((agent) => {
              const Icon = agent.icon
              return (
                <button
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent.id)}
                  className={clsx(
                    "card text-left transition-all p-4",
                    selectedAgent === agent.id
                      ? "ring-2 ring-primary-500 bg-primary-50"
                      : "hover:shadow-lg"
                  )}
                >
                  <div className="p-2 rounded-lg w-fit bg-gray-100">
                    <Icon className="w-5 h-5 text-gray-700" />
                  </div>
                  <h3 className="mt-3 font-semibold text-gray-900 text-sm">{agent.name}</h3>
                  <p className="mt-1 text-xs text-gray-500 line-clamp-2">{agent.description}</p>
                  {agent.features && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {agent.features.slice(0, 2).map((f, i) => (
                        <span key={i} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Agent Input Form */}
      {selectedAgent && (
        <div className="card">
          <div className="flex items-center gap-3 mb-4">
            {(() => {
              const agent = getAgentConfig(selectedAgent)
              const Icon = agent?.icon || Bot
              return (
                <>
                  <div className="p-2 rounded-lg bg-primary-100">
                    <Icon className="w-5 h-5 text-primary-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{agent?.name}</h3>
                    <p className="text-sm text-gray-500">{agent?.description}</p>
                  </div>
                </>
              )
            })()}
          </div>

          {/* Features list */}
          {getAgentConfig(selectedAgent)?.features && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <span className="text-xs font-medium text-gray-500">Capabilities:</span>
              <div className="mt-1 flex flex-wrap gap-2">
                {getAgentConfig(selectedAgent).features.map((f, i) => (
                  <span key={i} className="text-xs bg-white border border-gray-200 text-gray-700 px-2 py-1 rounded-full">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {getAgentConfig(selectedAgent)?.inputLabel}
                </label>
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={getAgentConfig(selectedAgent)?.inputPlaceholder}
                  className="input w-full"
                  disabled={isLoading}
                />
              </div>

              {['incident', 'crossdomain', 'notification'].includes(getAgentConfig(selectedAgent)?.inputType) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value)}
                    className="input w-full"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                </div>
              )}

              {['crossdomain', 'notification'].includes(getAgentConfig(selectedAgent)?.inputType) && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Event Type</label>
                    <select
                      value={eventType}
                      onChange={(e) => setEventType(e.target.value)}
                      className="input w-full"
                    >
                      <option value="incident">Incident</option>
                      <option value="change">Change</option>
                      <option value="deprecation">Deprecation</option>
                      <option value="alert">Alert</option>
                    </select>
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Describe the event..."
                      className="input w-full h-20"
                    />
                  </div>
                </>
              )}
            </div>

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
                  Run Agent
                </>
              )}
            </button>
          </form>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Results</h3>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {results.map((result, idx) => {
              const agent = getAgentConfig(result.agentId)
              const Icon = agent?.icon || Bot
              return (
                <div key={idx} className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className="w-4 h-4 text-primary-600" />
                    <span className="font-medium text-gray-900">{agent?.name}</span>
                    <span className="text-sm text-gray-500">
                      {new Date(result.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <pre className="text-sm text-gray-600 whitespace-pre-wrap overflow-x-auto max-h-64 overflow-y-auto">
                    {typeof result.data === 'object'
                      ? JSON.stringify(result.data, null, 2)
                      : result.data}
                  </pre>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {!selectedAgent && results.length === 0 && (
        <div className="card text-center py-12">
          <Bot className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900">Select an Agent</h3>
          <p className="text-gray-500 mt-1">
            Choose an AI agent above to get started with intelligent data governance
          </p>
        </div>
      )}
    </div>
  )
}
