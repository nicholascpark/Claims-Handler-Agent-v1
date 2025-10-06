import { useState, useRef } from 'react'

function ChatInput({ onSendText, onSendImage, isDisabled, isSessionActive }) {
  const [message, setMessage] = useState('')
  const [selectedImage, setSelectedImage] = useState(null)
  const [imagePreview, setImagePreview] = useState(null)
  const fileInputRef = useRef(null)

  const handleSendText = () => {
    if (message.trim() && !isDisabled) {
      onSendText(message.trim())
      setMessage('')
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendText()
    }
  }

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert('Please select an image file')
        return
      }

      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('Image size must be less than 10MB')
        return
      }

      setSelectedImage(file)

      // Create preview
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleSendImage = async () => {
    if (selectedImage && !isDisabled) {
      const reader = new FileReader()
      reader.onloadend = () => {
        const base64 = reader.result.split(',')[1] // Remove data:image/xxx;base64, prefix
        onSendImage({
          data: base64,
          mimeType: selectedImage.type,
          name: selectedImage.name,
          size: selectedImage.size
        })
        
        // Clear selection
        setSelectedImage(null)
        setImagePreview(null)
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }
      reader.readAsDataURL(selectedImage)
    }
  }

  const handleClearImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="bg-white border-t border-gray-300 p-4">
      {/* Image Preview */}
      {imagePreview && (
        <div className="mb-3 flex items-start space-x-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <img 
            src={imagePreview} 
            alt="Preview" 
            className="w-20 h-20 object-cover rounded"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">
              {selectedImage?.name}
            </p>
            <p className="text-xs text-gray-500">
              {(selectedImage?.size / 1024).toFixed(1)} KB
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleSendImage}
              disabled={isDisabled || !isSessionActive}
              className="px-3 py-1.5 bg-intact-red text-white text-sm rounded hover:bg-intact-dark-red disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Send image"
            >
              Send
            </button>
            <button
              onClick={handleClearImage}
              className="px-3 py-1.5 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 transition-colors"
              title="Clear image"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="flex items-end space-x-2">
        {/* Image Upload Button */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageSelect}
          className="hidden"
          disabled={isDisabled || !isSessionActive}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={isDisabled || !isSessionActive}
          className="flex-shrink-0 p-2.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          title="Attach image"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </button>

        {/* Text Input */}
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={isSessionActive ? "Type a message or use voice..." : "Start a session to send messages"}
          disabled={isDisabled || !isSessionActive}
          rows={1}
          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-intact-red focus:border-transparent resize-none disabled:bg-gray-100 disabled:cursor-not-allowed transition-all"
        />

        {/* Send Button */}
        <button
          onClick={handleSendText}
          disabled={isDisabled || !isSessionActive || !message.trim()}
          className="flex-shrink-0 px-5 py-2.5 bg-intact-red text-white rounded-lg hover:bg-intact-dark-red disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          title="Send message"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
          <span className="hidden sm:inline">Send</span>
        </button>
      </div>

      {/* Helper Text */}
      <p className="mt-2 text-xs text-gray-500">
        {isSessionActive 
          ? "Press Enter to send, Shift+Enter for new line. Images up to 10MB supported."
          : "Start a session to enable text and image input"}
      </p>
    </div>
  )
}

export default ChatInput

