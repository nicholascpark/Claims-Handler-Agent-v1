function CallAgentButton({ isSessionActive, onStart, onStop }) {
  const handleClick = () => {
    if (isSessionActive) {
      onStop()
    } else {
      onStart()
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`
        px-8 py-4 rounded-lg font-semibold text-lg
        transition-all duration-200 transform hover:scale-105
        focus:outline-none focus:ring-4 focus:ring-offset-2
        ${isSessionActive 
          ? 'bg-gray-700 hover:bg-gray-800 text-white focus:ring-gray-400' 
          : 'bg-intact-red hover:bg-intact-dark-red text-white focus:ring-red-400 shadow-lg'
        }
      `}
    >
      <div className="flex items-center space-x-3">
        {isSessionActive ? (
          <>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 3l-6 6m0 0V4m0 5h5M5 3a2 2 0 00-2 2v1c0 8.284 6.716 15 15 15h1a2 2 0 002-2v-3.28a1 1 0 00-.684-.948l-4.493-1.498a1 1 0 00-1.21.502l-1.13 2.257a11.042 11.042 0 01-5.516-5.517l2.257-1.128a1 1 0 00.502-1.21L9.228 3.683A1 1 0 008.279 3H5z" />
            </svg>
            <span>End Call</span>
          </>
        ) : (
          <>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            <span>Call Agent</span>
          </>
        )}
      </div>
    </button>
  )
}

export default CallAgentButton
