import { useState } from 'react'

function JsonPayloadDisplay({ claimData, isComplete }) {
  const [isExpanded, setIsExpanded] = useState(true)

  // Calculate completion progress
  const calculateProgress = () => {
    if (!claimData || Object.keys(claimData).length === 0) return 0
    
    const requiredFields = [
      'claimant.insured_name',
      'claimant.insured_phone', 
      'incident.incident_date',
      'incident.incident_time',
      'incident.incident_location',
      'incident.incident_description',
      'property_damage.property_type',
      'property_damage.points_of_impact',
      'property_damage.damage_description',
      'property_damage.estimated_damage_severity'
    ]
    
    const getValue = (obj, path) => {
      const keys = path.split('.')
      let current = obj
      for (const key of keys) {
        if (current && typeof current === 'object') {
          current = current[key]
        } else {
          return null
        }
      }
      return current
    }
    
    const filledFields = requiredFields.filter(field => {
      const value = getValue(claimData, field)
      if (Array.isArray(value)) return value.length > 0
      return value && String(value).trim() !== ''
    })
    
    return Math.round((filledFields.length / requiredFields.length) * 100)
  }

  const progress = calculateProgress()

  return (
    <div className="bg-white border border-gray-300 rounded-lg shadow-sm flex flex-col h-[600px]">
      {/* Header */}
      <div className="bg-gray-50 border-b border-gray-300 px-4 py-3 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Claim Data Payload
            </h2>
            <p className="text-sm text-gray-600">
              Live JSON object - updates dynamically
            </p>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 hover:bg-gray-200 rounded-md transition-colors"
            aria-label={isExpanded ? 'Collapse' : 'Expand'}
          >
            <svg 
              className={`w-5 h-5 text-gray-600 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Progress Bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
            <span>Completion Progress</span>
            <span className="font-semibold">{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                isComplete ? 'bg-green-600' : 'bg-intact-red'
              }`}
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          {isComplete && (
            <div className="mt-2 flex items-center text-sm text-green-700 font-medium">
              <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              Claim Complete
            </div>
          )}
        </div>
      </div>

      {/* JSON Display */}
      {isExpanded && (
        <div className="flex-1 overflow-y-auto p-4">
          {Object.keys(claimData).length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="mt-2 text-sm">No claim data yet</p>
                <p className="mt-1 text-xs text-gray-400">Data will appear as conversation progresses</p>
              </div>
            </div>
          ) : (
            <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap break-words">
              {JSON.stringify(claimData, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

export default JsonPayloadDisplay
