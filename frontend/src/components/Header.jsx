function Header() {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center space-x-3">
          <img 
            src="/intactbot_logo.png" 
            alt="IntactBot Logo" 
            className="h-12 w-auto"
          />
          <div className="border-l border-gray-300 pl-3">
            <h1 className="text-xl font-semibold text-gray-900">
              FNOL Voice Agent
            </h1>
            <p className="text-sm text-gray-600">
              First Notice of Loss - Claim Intake
            </p>
          </div>
        </div>

        {/* Company Branding */}
        <div className="hidden md:block text-right">
          <p className="text-lg font-semibold text-gray-900">
            Intact Specialty Insurance
          </p>
          <p className="text-sm text-gray-600">Claims Department</p>
        </div>
      </div>
    </header>
  )
}

export default Header
