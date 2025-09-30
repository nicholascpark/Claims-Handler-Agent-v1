function StatusIndicator({ isConnected, isSessionActive, agentStatus }) {
  const getStatusColor = () => {
    if (!isConnected) return 'bg-gray-400'
    if (!isSessionActive) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const getStatusText = () => {
    if (!isConnected) return 'Disconnected'
    if (!isSessionActive) return 'Connected - Ready'
    return agentStatus || 'Active Session'
  }

  return (
    <div className="flex items-center space-x-3">
      <div className="flex items-center space-x-2">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()} animate-pulse`}></div>
        <span className="text-sm font-medium text-gray-700">
          {getStatusText()}
        </span>
      </div>
      {isSessionActive && (
        <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
          🎙️ Audio is the primary interaction
        </div>
      )}
    </div>
  )
}

export default StatusIndicator
