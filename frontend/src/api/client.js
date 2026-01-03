import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats').then(r => r.data)
export const getHealthByDomain = () => api.get('/dashboard/health-by-domain').then(r => r.data)

// Products
export const getProducts = (params = {}) => api.get('/products', { params }).then(r => r.data)
export const getProduct = (id) => api.get(`/products/${id}`).then(r => r.data)
export const getProductHealth = (id) => api.get(`/products/${id}/health`).then(r => r.data)
export const getProductContracts = (id) => api.get(`/products/${id}/contracts`).then(r => r.data)
export const getProductIncidents = (id, status) => api.get(`/products/${id}/incidents`, { params: { status } }).then(r => r.data)
export const getProductLineage = (id, depth = 3) => api.get(`/products/${id}/lineage`, { params: { depth } }).then(r => r.data)

// Domains
export const getDomains = () => api.get('/domains').then(r => r.data)
export const getDomain = (id) => api.get(`/domains/${id}`).then(r => r.data)
export const getDomainProducts = (id) => api.get(`/domains/${id}/products`).then(r => r.data)
export const createDomain = (data) => api.post('/domains', data).then(r => r.data)

// Contracts
export const getContracts = () => api.get('/contracts').then(r => r.data)
export const getContract = (id) => api.get(`/contracts/${id}`).then(r => r.data)
export const getContractRules = (id) => api.get(`/contracts/${id}/rules`).then(r => r.data)
export const createContract = (data) => api.post('/contracts', data).then(r => r.data)
export const validateData = (data) => api.post('/contracts/validate', data).then(r => r.data)
export const validateProductData = (productId, data) => api.post(`/contracts/${productId}/validate`, data).then(r => r.data)

// Lineage
export const getLineage = (productId) => api.get(`/lineage/${productId}/upstream`).then(r => r.data)
export const getImpact = (productId) => api.get(`/lineage/${productId}/impact`).then(r => r.data)

// Incidents
export const getIncidents = (params = {}) => api.get('/incidents', { params }).then(r => r.data)
export const getIncident = (id) => api.get(`/incidents/${id}`).then(r => r.data)
export const createIncident = (data) => api.post('/incidents', data).then(r => r.data)
export const handleIncident = (id, severity = 'medium') => api.post(`/incidents/${id}/handle`, null, { params: { severity } }).then(r => r.data)
export const updateIncident = (id, data) => api.patch(`/incidents/${id}`, data).then(r => r.data)
export const getIncidentStats = () => api.get('/incidents/stats/summary').then(r => r.data)

// Pipelines
export const getPipelines = () => api.get('/pipelines').then(r => r.data)
export const getPipeline = (id) => api.get(`/pipelines/${id}`).then(r => r.data)
export const createPipeline = (data) => api.post('/pipelines', data).then(r => r.data)
export const runPipeline = (id) => api.post(`/pipelines/${id}/run`).then(r => r.data)

// Policies
export const getPolicies = (params = {}) => api.get('/policies', { params }).then(r => r.data)
export const getPolicy = (id) => api.get(`/policies/${id}`).then(r => r.data)
export const createPolicy = (data) => api.post('/policies', data).then(r => r.data)
export const updatePolicy = (id, data) => api.patch(`/policies/${id}`, data).then(r => r.data)
export const applyPolicy = (policyId, targetType, targetId) =>
  api.post(`/policies/${policyId}/apply`, null, { params: { target_type: targetType, target_id: targetId } }).then(r => r.data)

// Marketplace
export const searchMarketplace = (query) => api.get(`/marketplace/search?q=${encodeURIComponent(query)}`).then(r => r.data)

// Agents - Core
export const runDiscoveryAgent = (query) => api.post('/agents/discovery', { query }).then(r => r.data)
export const runQAAgent = (question) => api.post('/agents/qa', { query: question }).then(r => r.data)
export const runImpactAgent = (productId) => api.post('/agents/impact', { product_id: productId }).then(r => r.data)
export const runHealingAgent = (incidentId, severity) => api.post('/agents/healing', { incident_id: incidentId, severity }).then(r => r.data)
export const runStewardAgent = (incidentId, severity) => api.post('/agents/steward', { incident_id: incidentId, severity }).then(r => r.data)

// Agents - Advanced (P2-P3)
export const runPredictiveAgent = (productIds) => api.post('/agents/predictive', { product_ids: productIds }).then(r => r.data)
export const runOrchestratorAgent = (incidentIds) => api.post('/agents/orchestrator', { incident_ids: incidentIds }).then(r => r.data)
export const runContractEvolutionAgent = (contractId) => api.post('/agents/contract-evolution', { contract_id: contractId }).then(r => r.data)
export const runCrossDomainAgent = (eventType, productId, severity, description) =>
  api.post('/agents/cross-domain', { event_type: eventType, product_id: productId, severity, description }).then(r => r.data)
export const runNotificationAgent = (eventType, severity, productId, summary, details) =>
  api.post('/agents/notification', { event_type: eventType, severity, product_id: productId, summary, details }).then(r => r.data)

// Agents - SLA and Insights
export const runSLAMonitorAgent = (productIds = null) =>
  api.post('/agents/sla-monitor', { product_ids: productIds }).then(r => r.data)
export const runInsightsAgent = (timeRangeDays = 30) =>
  api.post('/agents/insights', { time_range_days: timeRangeDays }).then(r => r.data)

// Supervisor Agent (Global Orchestrator)
export const runSupervisorAgent = (query, conversationHistory = null, autoApprove = true) =>
  api.post('/agents/supervisor', { query, conversation_history: conversationHistory, auto_approve: autoApprove }).then(r => r.data)
export const getSupervisorCapabilities = () => api.get('/agents/supervisor/capabilities').then(r => r.data)

// Agents - List Available
export const getAvailableAgents = () => api.get('/agents/available').then(r => r.data)

// Agents - Streaming (SSE)
export const streamHealingAgent = (incidentId, severity, onMessage) => {
  const eventSource = new EventSource(`/api/agents/healing/stream?incident_id=${incidentId}&severity=${severity}`)
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onMessage(data)
    if (data.status === 'completed' || data.status === 'error') {
      eventSource.close()
    }
  }
  eventSource.onerror = () => eventSource.close()
  return eventSource
}

export const streamInsightsAgent = (timeRangeDays, onMessage) => {
  const eventSource = new EventSource(`/api/agents/insights/stream?time_range_days=${timeRangeDays}`)
  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    onMessage(data)
    if (data.status === 'completed' || data.status === 'error') {
      eventSource.close()
    }
  }
  eventSource.onerror = () => eventSource.close()
  return eventSource
}

export const streamSupervisorAgent = (query, onMessage) => {
  // For SSE with POST, we need to use fetch with ReadableStream
  const controller = new AbortController()

  fetch('/api/agents/supervisor/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, auto_approve: true }),
    signal: controller.signal
  }).then(response => {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    function read() {
      reader.read().then(({ done, value }) => {
        if (done) return
        const text = decoder.decode(value)
        const lines = text.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              onMessage(data)
            } catch (e) {}
          }
        }
        read()
      })
    }
    read()
  }).catch(err => {
    if (err.name !== 'AbortError') {
      onMessage({ status: 'error', error: err.message })
    }
  })

  return { abort: () => controller.abort() }
}

// Human-in-the-Loop (HITL)
export const getPendingReviews = (decisionType = null) =>
  api.get('/hitl/pending', { params: { decision_type: decisionType } }).then(r => r.data)
export const submitReview = (requestId, decision, decidedBy, outcome = 'approved') =>
  api.post('/hitl/submit', { request_id: requestId, decision, decided_by: decidedBy, outcome }).then(r => r.data)
export const getReviewStats = () => api.get('/hitl/stats').then(r => r.data)

// Feedback
export const submitFeedback = (feedbackType, targetId, targetType, originalValue, feedbackValue, context = {}) =>
  api.post('/feedback', { feedback_type: feedbackType, target_id: targetId, target_type: targetType,
    original_value: originalValue, feedback_value: feedbackValue, context }).then(r => r.data)
export const getFeedbackStats = (targetType) => api.get('/feedback/stats', { params: { target_type: targetType } }).then(r => r.data)

// Observability
export const getSystemMetrics = () => api.get('/observability/metrics').then(r => r.data)
export const getActiveTraces = () => api.get('/observability/traces').then(r => r.data)
export const getHealthChecks = () => api.get('/observability/health').then(r => r.data)

// Intelligence (Graph RAG)
export const intelligenceQuery = (question) => api.post('/intelligence/query', { question }).then(r => r.data)
export const intelligenceCypher = (question) => api.post('/intelligence/cypher', { question }).then(r => r.data)
export const intelligenceExtract = (text, source) => api.post('/intelligence/extract', { text, source }).then(r => r.data)
export const intelligenceInsights = () => api.get('/intelligence/insights').then(r => r.data)

// Metrics
export const getMetrics = (productId) => api.get(`/metrics/${productId}/error_rate`).then(r => r.data)

// Users
export const getUsers = () => api.get('/users').then(r => r.data)
export const getUser = (id) => api.get(`/users/${id}`).then(r => r.data)
export const createUser = (data) => api.post('/users', data).then(r => r.data)

// Tags
export const getTags = () => api.get('/tags').then(r => r.data)
export const getTag = (id) => api.get(`/tags/${id}`).then(r => r.data)
export const createTag = (data) => api.post('/tags', data).then(r => r.data)
export const applyTag = (tagId, productId) => api.post(`/tags/${tagId}/apply/${productId}`).then(r => r.data)

// SLAs
export const getSLAs = () => api.get('/slas').then(r => r.data)
export const getSLA = (id) => api.get(`/slas/${id}`).then(r => r.data)
export const getSLAStatus = (id) => api.get(`/slas/${id}/status`).then(r => r.data)
export const createSLA = (data) => api.post('/slas', data).then(r => r.data)

// Data Ingestion
export const ingestCSV = (productId, file, validate = true) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/ingest/csv/${productId}?validate=${validate}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)
}

export const ingestJSON = (productId, file, validate = true) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/ingest/json/${productId}?validate=${validate}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)
}

export const ingestRecords = (productId, records, validate = true) =>
  api.post(`/ingest/records/${productId}?validate=${validate}`, records).then(r => r.data)

// Global Search
export const globalSearch = (query, limit = 20) =>
  api.get('/search', { params: { q: query, limit } }).then(r => r.data)

// Health Check
export const getHealth = () => api.get('/health').then(r => r.data)

export default api
