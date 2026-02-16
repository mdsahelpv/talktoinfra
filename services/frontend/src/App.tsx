import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';
import { useAuthStore } from '@/stores';
import { apiClient } from '@/api/client';
import Layout from '@/components/layout/Layout';
import LoginPage from '@/pages/LoginPage';
import ChatPage from '@/pages/ChatPage';
import DashboardPage from '@/pages/DashboardPage';
import InfraPage from '@/pages/InfraPage';
import ActionsPage from '@/pages/ActionsPage';
import ApprovalsPage from '@/pages/ApprovalsPage';
import SettingsPage from '@/pages/SettingsPage';
import WorkflowDashboard from '@/pages/WorkflowDashboard';
import WorkflowExecutionView from '@/pages/WorkflowExecutionView';

function App() {
  const { isAuthenticated, token, logout } = useAuthStore();

  // Initialize API client token immediately on render (before children mount)
  // This prevents race conditions where child components make API calls before token is set
  const tokenRef = useRef(token);
  if (tokenRef.current !== token) {
    apiClient.setToken(token);
    tokenRef.current = token;
  }

  // Also handle token changes via effect for external updates
  useEffect(() => {
    apiClient.setToken(token);
  }, [token]);

  // Setup auth error handler to logout on 401/403
  useEffect(() => {
    apiClient.setOnAuthError(() => {
      logout();
    });
  }, [logout]);

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" /> : <LoginPage />}
      />
      <Route
        path="/"
        element={isAuthenticated ? <Layout /> : <Navigate to="/login" />}
      >
        <Route index element={<Navigate to="/chat" />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="infra" element={<InfraPage />} />
        <Route path="actions" element={<ActionsPage />} />
        <Route path="approvals" element={<ApprovalsPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="workflows" element={<WorkflowDashboard />} />
        <Route path="workflows/:id" element={<WorkflowDashboard />} />
        <Route path="executions/:executionId" element={<WorkflowExecutionView />} />
      </Route>
    </Routes>
  );
}

export default App;
