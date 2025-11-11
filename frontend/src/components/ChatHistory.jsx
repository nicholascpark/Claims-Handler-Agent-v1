import { useEffect, useRef } from 'react'

function formatTimestamp(ts) {
  if (!ts) return ''
  let d = null
  if (typeof ts === 'number') {
    d = new Date(ts)
  } else if (ts instanceof Date) {
    d = ts
  } else if (typeof ts === 'string' && /^\d{2}:\d{2}(:\d{2})?$/.test(ts)) {
    const [h, m, s = '0'] = ts.split(':')
    const now = new Date()
    now.setHours(parseInt(h, 10), parseInt(m, 10), parseInt(s, 10), 0)
    d = now
  } else {
    const parsed = new Date(ts)
    if (!isNaN(parsed.getTime())) d = parsed
  }
  if (!d) return String(ts)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

function ChatHistory({ messages }) {
  const messagesEndRef = useRef(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="bg-white border border-gray-300 rounded-lg shadow-sm flex flex-col h-[600px]">
      {/* Header */}
      <div className="bg-gray-50 border-b border-gray-300 px-4 py-3 rounded-t-lg">
        <h2 className="text-lg font-semibold text-gray-900">
          Chat History
        </h2>
        <p className="text-sm text-gray-600">
          Real-time conversation transcript
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <p className="mt-2 text-sm">No messages yet</p>
              <p className="mt-1 text-xs text-gray-400">Click "Call Agent" to start</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] rounded-lg px-4 py-2 ${
                    msg.role === 'user'
                      ? 'bg-gray-200 text-gray-900'
                      : 'bg-gray-800 text-white'
                  }`}
                >
                  <div className="flex items-start space-x-2">
                    <div className="flex-shrink-0 mt-1">
                      {msg.role === 'user' ? (
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-2 0c0 .993-.241 1.929-.668 2.754l-1.524-1.525a3.997 3.997 0 00.078-2.183l1.562-1.562C15.802 8.249 16 9.1 16 10zm-5.165 3.913l1.58 1.58A5.98 5.98 0 0110 16a5.976 5.976 0 01-2.516-.552l1.562-1.562a4.006 4.006 0 001.789.027zm-4.677-2.796a4.002 4.002 0 01-.041-2.08l-.08.08-1.53-1.533A5.98 5.98 0 004 10c0 .954.223 1.856.619 2.657l1.54-1.54zm1.088-6.45A5.974 5.974 0 0110 4c.954 0 1.856.223 2.657.619l-1.54 1.54a4.002 4.002 0 00-2.346.033L7.246 4.668zM12 10a2 2 0 11-4 0 2 2 0 014 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <div className="flex-1">
                      {/* Text Content */}
                      {msg.content && <p className="text-sm whitespace-pre-wrap">{msg.content}</p>}
                      
                      {/* Image Content */}
                      {msg.image && (
                        <div className="mt-2">
                          <img 
                            src={msg.image} 
                            alt="Uploaded" 
                            className="max-w-full h-auto rounded-lg border border-gray-200 max-h-64 object-contain"
                            loading="lazy"
                          />
                          {msg.imageName && (
                            <p className="text-xs mt-1 text-gray-500">{msg.imageName}</p>
                          )}
                        </div>
                      )}
                      
                      {/* Timestamp */}
                      {msg.timestamp && (
                        <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-gray-600' : 'text-gray-400'}`}>
                          {formatTimestamp(msg.timestamp)}
                        </p>
                      )}
                      
                      {/* Message Type Indicator */}
                      {msg.type && (
                        <span className={`text-xs ${msg.role === 'user' ? 'text-gray-500' : 'text-gray-400'}`}>
                          {msg.type === 'text' && '💬'}
                          {msg.type === 'voice' && '🎤'}
                          {msg.type === 'image' && '🖼️'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
    </div>
  )
}

export default ChatHistory
