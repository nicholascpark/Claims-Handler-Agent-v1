import { useState, useEffect } from 'react'
import Header from './components/Header'
import CallAgentButton from './components/CallAgentButton'
import ChatHistory from './components/ChatHistory'
import ChatInput from './components/ChatInput'
import JsonPayloadDisplay from './components/JsonPayloadDisplay'
import StatusIndicator from './components/StatusIndicator'
import MicrophoneSelector from './components/MicrophoneSelector'
import { useVoiceAgent } from './hooks/useVoiceAgent'

function App() {
  const [chatVisible, setChatVisible] = useState(true)
  
  const {
    isConnected,
    isSessionActive,
    messages,
    claimData,
    isClaimComplete,
    agentStatus,
    error,
    startSession,
    stopSession,
    sendTextMessage,
    sendImage,
    microphones,
    selectedDeviceId,
    setSelectedDeviceId,
    refreshAudioDevices,
    isEnumeratingDevices,
    permissionsGranted,
    requestDevicePermission,
  } = useVoiceAgent()

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <Header />

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col p-6 space-y-4">
        {/* Status Bar */}
        <div className="flex items-center justify-between">
          <StatusIndicator
            isConnected={isConnected}
            isSessionActive={isSessionActive}
            agentStatus={agentStatus}
          />
          
          {/* Toggle Chat Visibility */}
          <button
            onClick={() => setChatVisible(!chatVisible)}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            {chatVisible ? 'Hide Chat' : 'Show Chat'}
          </button>
        </div>

        {/* Microphone selector + Call Agent Button */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <MicrophoneSelector
            microphones={microphones}
            selectedDeviceId={selectedDeviceId}
            onChange={setSelectedDeviceId}
            onRefresh={() => refreshAudioDevices(false)}
            isEnumerating={isEnumeratingDevices}
            isDisabled={isSessionActive}
            permissionsGranted={permissionsGranted}
            requestPermission={requestDevicePermission}
          />
          <CallAgentButton
            isSessionActive={isSessionActive}
            onStart={startSession}
            onStop={stopSession}
          />
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-intact-red" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">Connection Error</h3>
                <p className="mt-1 text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Main Layout: Chat History and JSON Payload */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Panel: Chat History with Input */}
          {chatVisible && (
            <div className="flex flex-col space-y-4">
              <ChatHistory messages={messages} />
              <ChatInput 
                onSendText={sendTextMessage}
                onSendImage={sendImage}
                isDisabled={!isConnected}
                isSessionActive={isSessionActive}
              />
            </div>
          )}

          {/* Right Panel: JSON Payload */}
          <div className={`flex flex-col ${!chatVisible ? 'lg:col-span-2' : ''}`}>
            <JsonPayloadDisplay
              claimData={claimData}
              isComplete={isClaimComplete}
            />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-4 px-6">
        <div className="text-center text-sm text-gray-500">
          <p>© 2025 Intact Specialty Insurance. All rights reserved.</p>
          <p className="mt-1">First Notice of Loss (FNOL) Voice Agent</p>
        </div>
      </footer>
    </div>
  )
}

export default App
