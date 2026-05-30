import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/shared/Layout'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Sessions from './pages/Sessions'
import Audit from './pages/Audit'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
