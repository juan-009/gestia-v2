import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { 
  LoginCredentials, 
  LoginResponse, 
  MfaVerificationPayload, 
  VerificationResponse, 
  User 
} from '../../types';
import { RootState } from '../../store/store';

// Create API slice with RTK Query
export const authApi = createApi({
  reducerPath: 'authApi',
  baseQuery: fetchBaseQuery({ 
    baseUrl: import.meta.env.VITE_API_URL || 'http://localhost:5173',
    prepareHeaders: (headers, { getState }) => {
      // Add request source and ID headers
      headers.set('X-Request-Source', 'web');
      headers.set('X-Request-ID', crypto.randomUUID());
      
      // Add auth token if available
      const token = (getState() as RootState).auth.isAuthenticated 
        ? localStorage.getItem('accessToken') 
        : null;
        
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      
      return headers;
    },
    credentials: 'include', // Include cookies for refresh token
  }),
  endpoints: (builder) => ({
    // Login endpoint
    login: builder.mutation<LoginResponse, LoginCredentials>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
    }),
    
    // MFA verification endpoint
    verifyMfa: builder.mutation<VerificationResponse, MfaVerificationPayload>({
      query: (payload) => ({
        url: '/auth/mfa/verify',
        method: 'POST',
        body: payload,
      }),
    }),
    
    // Logout endpoint
    logout: builder.mutation<void, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
    }),
    
    // Password recovery request
    requestPasswordRecovery: builder.mutation<{ message: string }, { email: string }>({
      query: (payload) => ({
        url: '/auth/password/recovery',
        method: 'POST',
        body: payload,
      }),
    }),
    
    // Reset password with token
    resetPassword: builder.mutation<{ message: string }, { token: string; password: string; confirmPassword: string }>({
      query: (payload) => ({
        url: '/auth/password/reset',
        method: 'POST',
        body: payload,
      }),
    }),
    
    // Get current user info
    getCurrentUser: builder.query<User, void>({
      query: () => '/auth/me',
    }),
    
    // Change password (authenticated)
    changePassword: builder.mutation<{ message: string }, { currentPassword: string; newPassword: string; confirmPassword: string }>({
      query: (payload) => ({
        url: '/auth/password/change',
        method: 'POST',
        body: payload,
      }),
    }),
    
    // Enable MFA
    enableMfa: builder.mutation<{ secret: string; qrCode: string }, { type: 'totp' | 'webauthn' }>({
      query: (payload) => ({
        url: '/auth/mfa/enable',
        method: 'POST',
        body: payload,
      }),
    }),
    
    // Disable MFA
    disableMfa: builder.mutation<{ message: string }, { type: 'totp' | 'webauthn'; password: string }>({
      query: (payload) => ({
        url: '/auth/mfa/disable',
        method: 'POST',
        body: payload,
      }),
    }),
    
    // Refresh access token
    refreshToken: builder.mutation<{ accessToken: string }, void>({
      query: () => ({
        url: '/auth/refresh',
        method: 'POST',
      }),
    }),
  }),
});

// Export hooks for usage in components
export const {
  useLoginMutation,
  useVerifyMfaMutation,
  useLogoutMutation,
  useRequestPasswordRecoveryMutation,
  useResetPasswordMutation,
  useGetCurrentUserQuery,
  useChangePasswordMutation,
  useEnableMfaMutation,
  useDisableMfaMutation,
  useRefreshTokenMutation,
} = authApi;