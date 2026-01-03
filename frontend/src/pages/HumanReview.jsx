import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPendingReviews, submitReview, getReviewStats, submitFeedback } from '../api/client'
import {
  UserCheck, Clock, CheckCircle, XCircle, Edit3, AlertTriangle,
  ThumbsUp, ThumbsDown, MessageSquare, BarChart2, Loader2
} from 'lucide-react'
import clsx from 'clsx'

export default function HumanReview() {
  const queryClient = useQueryClient()
  const [selectedReview, setSelectedReview] = useState(null)
  const [modifiedDecision, setModifiedDecision] = useState('')
  const [feedbackComment, setFeedbackComment] = useState('')

  const { data: reviews = [], isLoading: reviewsLoading } = useQuery({
    queryKey: ['pending-reviews'],
    queryFn: () => getPendingReviews(),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const { data: stats } = useQuery({
    queryKey: ['review-stats'],
    queryFn: getReviewStats,
  })

  const submitMutation = useMutation({
    mutationFn: ({ requestId, decision, outcome }) =>
      submitReview(requestId, decision, 'current_user', outcome),
    onSuccess: () => {
      queryClient.invalidateQueries(['pending-reviews'])
      queryClient.invalidateQueries(['review-stats'])
      setSelectedReview(null)
      setModifiedDecision('')
    },
  })

  const feedbackMutation = useMutation({
    mutationFn: ({ targetId, rating, comment }) =>
      submitFeedback('rating', targetId, 'ai_decision', null, rating, { comment }),
    onSuccess: () => {
      setFeedbackComment('')
    },
  })

  const handleApprove = (review) => {
    submitMutation.mutate({
      requestId: review.id,
      decision: review.options?.[0] || 'approved',
      outcome: 'approved',
    })
  }

  const handleReject = (review) => {
    submitMutation.mutate({
      requestId: review.id,
      decision: 'rejected',
      outcome: 'rejected',
    })
  }

  const handleModify = (review) => {
    if (!modifiedDecision.trim()) return
    submitMutation.mutate({
      requestId: review.id,
      decision: modifiedDecision,
      outcome: 'modified',
    })
  }

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'text-red-600 bg-red-50'
      case 'high': return 'text-orange-600 bg-orange-50'
      case 'medium': return 'text-yellow-600 bg-yellow-50'
      case 'low': return 'text-green-600 bg-green-50'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  const getDecisionTypeIcon = (type) => {
    switch (type) {
      case 'severity_override': return AlertTriangle
      case 'contract_change': return Edit3
      case 'remediation_approval': return CheckCircle
      default: return UserCheck
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Human Review Queue</h1>
        <p className="text-gray-500">Review and approve AI-generated decisions</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-100">
              <Clock className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.pending || reviews.length}</div>
              <div className="text-sm text-gray-500">Pending Reviews</div>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-100">
              <CheckCircle className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.by_outcome?.approved || 0}</div>
              <div className="text-sm text-gray-500">Approved</div>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-100">
              <XCircle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">{stats?.by_outcome?.rejected || 0}</div>
              <div className="text-sm text-gray-500">Rejected</div>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-100">
              <BarChart2 className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-900">
                {stats?.avg_decision_time_seconds
                  ? `${Math.round(stats.avg_decision_time_seconds / 60)}m`
                  : 'N/A'}
              </div>
              <div className="text-sm text-gray-500">Avg Decision Time</div>
            </div>
          </div>
        </div>
      </div>

      {/* Review Queue */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Pending Reviews</h2>
          <button
            onClick={() => queryClient.invalidateQueries(['pending-reviews'])}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            Refresh
          </button>
        </div>

        {reviewsLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          </div>
        ) : reviews.length === 0 ? (
          <div className="text-center py-12">
            <UserCheck className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900">No Pending Reviews</h3>
            <p className="text-gray-500 mt-1">All AI decisions have been reviewed</p>
          </div>
        ) : (
          <div className="space-y-4">
            {reviews.map((review) => {
              const Icon = getDecisionTypeIcon(review.decision_type)
              const isSelected = selectedReview?.id === review.id

              return (
                <div
                  key={review.id}
                  className={clsx(
                    "border rounded-lg p-4 transition-all",
                    isSelected ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:border-gray-300"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <div className="p-2 rounded-lg bg-gray-100">
                        <Icon className="w-5 h-5 text-gray-700" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">
                            {review.decision_type?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </span>
                          {review.context?.severity && (
                            <span className={clsx(
                              "text-xs px-2 py-0.5 rounded-full font-medium",
                              getSeverityColor(review.context.severity)
                            )}>
                              {review.context.severity}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{review.description}</p>
                        <div className="text-xs text-gray-400 mt-2">
                          Created: {new Date(review.created_at).toLocaleString()}
                          {review.timeout_seconds && (
                            <span className="ml-2">
                              Timeout: {Math.round(review.timeout_seconds / 60)} min
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleApprove(review)}
                        disabled={submitMutation.isPending}
                        className="btn btn-sm bg-green-600 text-white hover:bg-green-700"
                      >
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(review)}
                        disabled={submitMutation.isPending}
                        className="btn btn-sm bg-red-600 text-white hover:bg-red-700"
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Reject
                      </button>
                      <button
                        onClick={() => setSelectedReview(isSelected ? null : review)}
                        className="btn btn-sm btn-secondary"
                      >
                        <Edit3 className="w-4 h-4 mr-1" />
                        Modify
                      </button>
                    </div>
                  </div>

                  {/* Context Details */}
                  {review.context && Object.keys(review.context).length > 0 && (
                    <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs font-medium text-gray-500 mb-2">Context:</div>
                      <pre className="text-xs text-gray-600 overflow-x-auto">
                        {JSON.stringify(review.context, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* Options */}
                  {review.options && review.options.length > 0 && (
                    <div className="mt-4">
                      <div className="text-xs font-medium text-gray-500 mb-2">Available Options:</div>
                      <div className="flex flex-wrap gap-2">
                        {review.options.map((opt, i) => (
                          <button
                            key={i}
                            onClick={() => {
                              setSelectedReview(review)
                              setModifiedDecision(typeof opt === 'object' ? JSON.stringify(opt) : opt)
                            }}
                            className="text-xs px-3 py-1.5 bg-white border border-gray-200 rounded-lg hover:border-primary-500 hover:text-primary-600"
                          >
                            {typeof opt === 'object' ? opt.label || JSON.stringify(opt) : opt}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Modify Section */}
                  {isSelected && (
                    <div className="mt-4 p-4 bg-white border border-gray-200 rounded-lg">
                      <div className="text-sm font-medium text-gray-700 mb-2">Modify Decision:</div>
                      <textarea
                        value={modifiedDecision}
                        onChange={(e) => setModifiedDecision(e.target.value)}
                        placeholder="Enter your modified decision..."
                        className="input w-full h-24 mb-3"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleModify(review)}
                          disabled={!modifiedDecision.trim() || submitMutation.isPending}
                          className="btn btn-primary"
                        >
                          {submitMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            'Submit Modified Decision'
                          )}
                        </button>
                        <button
                          onClick={() => {
                            setSelectedReview(null)
                            setModifiedDecision('')
                          }}
                          className="btn btn-secondary"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Feedback Section */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Provide Feedback on AI Decisions</h2>
        <p className="text-sm text-gray-500 mb-4">
          Help improve AI accuracy by providing feedback on recent decisions
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <ThumbsUp className="w-5 h-5 text-green-600" />
              <span className="font-medium">Accurate Decisions</span>
            </div>
            <p className="text-sm text-gray-500">Rate decisions that were helpful and accurate</p>
            <button
              onClick={() => feedbackMutation.mutate({ targetId: 'recent', rating: 5, comment: 'Accurate' })}
              className="btn btn-sm btn-secondary mt-3"
            >
              Submit Positive Feedback
            </button>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <ThumbsDown className="w-5 h-5 text-red-600" />
              <span className="font-medium">Needs Improvement</span>
            </div>
            <p className="text-sm text-gray-500">Flag decisions that need correction</p>
            <button
              onClick={() => feedbackMutation.mutate({ targetId: 'recent', rating: 2, comment: 'Needs improvement' })}
              className="btn btn-sm btn-secondary mt-3"
            >
              Submit Correction
            </button>
          </div>

          <div className="p-4 border border-gray-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <MessageSquare className="w-5 h-5 text-blue-600" />
              <span className="font-medium">Detailed Feedback</span>
            </div>
            <textarea
              value={feedbackComment}
              onChange={(e) => setFeedbackComment(e.target.value)}
              placeholder="Provide detailed feedback..."
              className="input w-full h-16 text-sm mt-2"
            />
            <button
              onClick={() => feedbackMutation.mutate({ targetId: 'recent', rating: 3, comment: feedbackComment })}
              disabled={!feedbackComment.trim()}
              className="btn btn-sm btn-primary mt-2"
            >
              Submit Feedback
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
