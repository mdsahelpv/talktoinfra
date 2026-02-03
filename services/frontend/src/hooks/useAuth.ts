import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores';
import { apiClient } from '@/api/client';
import type { User } from '@/types';

export function useAuth() {
  const { user, token, isAuthenticated, login, logout } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    apiClient.setToken(token);
  }, [token]);

  const handleLogin = async (userData: User, accessToken: string) => {
    login(userData, accessToken);
    navigate('/');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return {
    user,
    token,
    isAuthenticated,
    login: handleLogin,
    logout: handleLogout,
  };
}

export function useRequireAuth() {
  const { isAuthenticated, isLoading } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    // Only redirect if not loading and not authenticated
    if (!isLoading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isLoading, isAuthenticated, navigate]);

  return isAuthenticated;
}
