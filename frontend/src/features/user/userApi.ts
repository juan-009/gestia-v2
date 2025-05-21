import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { UserProfile, AuditLogEntry, Role, Permission } from '../../types';
import { RootState } from '../../store/store';

// Create API slice with RTK Query
export const userApi = createApi({
  reducerPath: 'userApi',
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
  tagTypes: ['Profile', 'AuditLogs', 'Roles', 'Permissions'],
  endpoints: (builder) => ({
    // Get user profile
    getUserProfile: builder.query<UserProfile, void>({
      query: () => '/auth/me/profile',
      providesTags: ['Profile'],
    }),
    
    // Update user profile
    updateUserProfile: builder.mutation<UserProfile, Partial<UserProfile>>({
      query: (profile) => ({
        url: '/auth/me/profile',
        method: 'PATCH',
        body: profile,
      }),
      invalidatesTags: ['Profile'],
    }),
    
    // Get user audit logs
    getUserAuditLogs: builder.query<AuditLogEntry[], { page?: number; limit?: number }>({
      query: ({ page = 1, limit = 10 }) => `/auth/me/audit-logs?page=${page}&limit=${limit}`,
      providesTags: ['AuditLogs'],
    }),
    
    // Get all roles (admin only)
    getRoles: builder.query<Role[], void>({
      query: () => '/auth/admin/roles',
      providesTags: ['Roles'],
    }),
    
    // Create role (admin only)
    createRole: builder.mutation<Role, Partial<Role>>({
      query: (role) => ({
        url: '/auth/admin/roles',
        method: 'POST',
        body: role,
      }),
      invalidatesTags: ['Roles'],
    }),
    
    // Update role (admin only)
    updateRole: builder.mutation<Role, { id: string; role: Partial<Role> }>({
      query: ({ id, role }) => ({
        url: `/auth/admin/roles/${id}`,
        method: 'PATCH',
        body: role,
      }),
      invalidatesTags: ['Roles'],
    }),
    
    // Delete role (admin only)
    deleteRole: builder.mutation<{ message: string }, string>({
      query: (id) => ({
        url: `/auth/admin/roles/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['Roles'],
    }),
    
    // Get all permissions (admin only)
    getPermissions: builder.query<Permission[], void>({
      query: () => '/auth/admin/permissions',
      providesTags: ['Permissions'],
    }),
    
    // Get all audit logs (admin only)
    getAllAuditLogs: builder.query<AuditLogEntry[], { page?: number; limit?: number; userId?: string }>({
      query: ({ page = 1, limit = 10, userId }) => {
        let url = `/auth/admin/audit-logs?page=${page}&limit=${limit}`;
        if (userId) url += `&userId=${userId}`;
        return url;
      },
      providesTags: ['AuditLogs'],
    }),
    
    // Revoke user session (admin only)
    revokeUserSession: builder.mutation<{ message: string }, { userId: string; sessionId: string }>({
      query: ({ userId, sessionId }) => ({
        url: `/auth/admin/users/${userId}/sessions/${sessionId}`,
        method: 'DELETE',
      }),
    }),
  }),
});

// Export hooks for usage in components
export const {
  useGetUserProfileQuery,
  useUpdateUserProfileMutation,
  useGetUserAuditLogsQuery,
  useGetRolesQuery,
  useCreateRoleMutation,
  useUpdateRoleMutation,
  useDeleteRoleMutation,
  useGetPermissionsQuery,
  useGetAllAuditLogsQuery,
  useRevokeUserSessionMutation,
} = userApi;