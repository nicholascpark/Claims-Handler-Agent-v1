function MicrophoneSelector({
  microphones,
  selectedDeviceId,
  onChange,
  onRefresh,
  isEnumerating,
  isDisabled,
  permissionsGranted,
  requestPermission,
}) {
  return (
    <div className="flex items-center space-x-3">
      <label className="text-sm text-gray-700">Microphone</label>
      <select
        className="min-w-[260px] rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
        value={selectedDeviceId || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={isDisabled || isEnumerating}
        title={permissionsGranted ? '' : 'Grant mic permission to see device names'}
      >
        {microphones.length === 0 ? (
          <option value="" disabled>
            {isEnumerating ? 'Scanning microphones…' : 'No microphones found'}
          </option>
        ) : null}
        {microphones.map((m) => (
          <option key={m.deviceId} value={m.deviceId}>
            {m.label || (m.deviceId === 'default' ? 'Default microphone' : 'Microphone')}
          </option>
        ))}
      </select>
      <button
        onClick={onRefresh}
        disabled={isEnumerating}
        className="px-2.5 py-1.5 text-sm border rounded-md text-gray-700 border-gray-300 hover:bg-gray-50 disabled:opacity-60"
      >
        {isEnumerating ? 'Refreshing…' : 'Refresh'}
      </button>
      {!permissionsGranted && (
        <button
          onClick={requestPermission}
          className="px-2.5 py-1.5 text-sm border rounded-md text-gray-700 border-gray-300 hover:bg-gray-50"
        >
          Show names
        </button>
      )}
    </div>
  )
}

export default MicrophoneSelector


