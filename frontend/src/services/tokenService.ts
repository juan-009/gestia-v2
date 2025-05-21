import { jwtDecode } from 'jwt-decode';
import { DecodedToken } from '../types';
import { apiService } from './api';

// In-memory storage for the access token
let accessToken: string | null = null;

// Token service
export const tokenService = {
  // Set the access token in memory
  setAccessToken: (token: string) => {
    accessToken = token;
    localStorage.setItem('accessToken', token);
  },

  // Get the access token from memory
  getAccessToken: () => {
    return accessToken;
  },

  // Parse and decode the JWT token
  decodeToken: (token: string): DecodedToken | null => {
    try {
      return jwtDecode<DecodedToken>(token);
    } catch (error) {
      console.error('Failed to decode token:', error);
      return null;
    }
  },

  // Check if the token is expired
  isTokenExpired: (token: string): boolean => {
    const decoded = tokenService.decodeToken(token);
    if (!decoded) return true;
    
    // Add a buffer of 30 seconds to account for network latency
    const currentTime = Math.floor(Date.now() / 1000) + 30;
    return decoded.exp < currentTime;
  },

  // Refresh the access token using the refresh token
  refreshToken: async (): Promise<boolean> => {
    try {
      const response = await apiService.post<{ accessToken: string }>('/auth/refresh', {});
      
      if (response.accessToken) {
        tokenService.setAccessToken(response.accessToken);
        return true;
      }
      
      return false;
    } catch (error) {
      console.error('Failed to refresh token:', error);
      tokenService.clearTokens();
      return false;
    }
  },

  // Clear all tokens (logout)
  clearTokens: () => {
    accessToken = null;
    // The refresh token is stored in an HttpOnly cookie and will be cleared by the backend
  },

  // Extract user info from token
  getUserFromToken: (): { userId: string; role: string; permissions: string[] } | null => {
    const token = tokenService.getAccessToken();
    if (!token) return null;
    
    const decoded = tokenService.decodeToken(token);
    if (!decoded) return null;
    
    return {
      userId: decoded.sub,
      role: decoded.role,
      permissions: decoded.permissions,
    };
  }
};