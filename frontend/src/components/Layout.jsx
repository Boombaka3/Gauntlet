// frontend/src/components/Layout.jsx
import Sidebar from './Sidebar.jsx'
import { ApiStatus } from './ApiStatus.jsx'

export default function Layout({ children }) {
  return (
    <div className="flex min-h-screen bg-gauntlet-bg">
      <Sidebar />
      <main className="ml-60 flex-1 min-h-screen bg-gauntlet-bg pb-8">
        {children}
      </main>
      <ApiStatus />
    </div>
  )
}
