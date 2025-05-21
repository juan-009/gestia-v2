import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { tokenService } from './tokenService';
import { ApiError } from '../types';

// Base API configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:5173',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'X-Request-Source': 'web',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add unique request ID
    config.headers['X-Request-ID'] = crypto.randomUUID();
    
    // Add auth token if available
    const token = tokenService.getAccessToken();
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };
    
    // Handle token expiration (401)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Try to refresh the token
        const refreshed = await tokenService.refreshToken();
        
        if (refreshed && originalRequest.headers) {
          // Update the auth header with new token
          originalRequest.headers['Authorization'] = `Bearer ${tokenService.getAccessToken()}`;
          // Retry the original request
          return api(originalRequest);
        }
      } catch (refreshError) {
        // If refresh fails, force logout
        tokenService.clearTokens();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    // Format error response
    const apiError: ApiError = {
      code: error.response?.data?.code || 'UNKNOWN_ERROR',
      message: error.response?.data?.message || 'An unexpected error occurred',
      details: error.response?.data?.details,
    };
    
    return Promise.reject(apiError);
  }
);

// API service methods
export const apiService = {
  get: <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return api.get(url, config).then((response: AxiosResponse<T>) => response.data);
  },
  
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    return api.post(url, data, config).then((response: AxiosResponse<T>) => response.data);
  },
  
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    return api.put(url, data, config).then((response: AxiosResponse<T>) => response.data);
  },
  
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> => {
    return api.patch(url, data, config).then((response: AxiosResponse<T>) => response.data);
  },
  
  delete: <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return api.delete(url, config).then((response: AxiosResponse<T>) => response.data);
  },
};

export default api;