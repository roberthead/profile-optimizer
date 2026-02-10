import axios from 'axios';
import { useAuth } from '@clerk/clerk-react';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL,
});

// Default export for convenience
export default api;

// Hook to use API with Auth
export const useApi = () => {
  const { getToken } = useAuth();

  const authenticatedApi = axios.create({
    baseURL,
  });

  authenticatedApi.interceptors.request.use(async (config) => {
    const token = await getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return authenticatedApi;
};
