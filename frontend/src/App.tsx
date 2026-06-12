import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, User, Briefcase, Settings2, Workflow } from 'lucide-react'
import { Dashboard } from './pages/Dashboard'
import { ApplicationDetail } from './pages/ApplicationDetail'
import { ProfilePage } from './pages/Profile'
import { Onboarding } from './pages/Onboarding'
import { PreferencesPage } from './pages/Preferences'
import { PipelinePage } from './pages/Pipeline'
import clsx from 'clsx'

const NAV = [
  { to: '/',            icon: LayoutDashboard, label: 'Dashboard',       end: true },
  { to: '/pipeline',    icon: Workflow,         label: 'Job Progress',   end: false },
  { to: '/preferences', icon: Settings2,       label: 'Preferences',    end: false },
  { to: '/profile',     icon: User,            label: 'Profile',        end: false },
]

function AppContent() {
  const { pathname } = useLocation()
  const isOnboarding = pathname === '/onboarding'

  if (isOnboarding) {
    return (
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
      </Routes>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-parchment-300 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-5 py-5 border-b border-parchment-300">
          <div className="p-1.5 bg-brand-600 rounded-lg">
            <Briefcase size={18} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-gray-800 text-sm leading-tight">JobTracker</p>
            <p className="text-[10px] text-brand-700">Powered by Claude AI</p>
          </div>
        </div>

        {/* Nav links */}
        <nav className="flex-1 p-3 space-y-1">
          {NAV.map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors',
                isActive
                  ? 'bg-brand-100 text-brand-700 font-semibold'
                  : 'text-gray-600 hover:text-gray-800 hover:bg-parchment-100'
              )}
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-parchment-300">
          <p className="text-[10px] text-gray-600 leading-relaxed">
            Find, score & apply to jobs with AI-tailored resumes.
          </p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-parchment-50">
        <div className="p-8 min-h-full">
          <Routes>
            <Route path="/"              element={<Dashboard />} />
            <Route path="/jobs/:id"      element={<ApplicationDetail />} />
            <Route path="/pipeline"      element={<PipelinePage />} />
            <Route path="/preferences"   element={<PreferencesPage />} />
            <Route path="/profile"       element={<ProfilePage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}
