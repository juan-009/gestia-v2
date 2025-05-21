// Common types for the entire application

// User types
export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
  permissions: string[];
  createdAt: string;
  updatedAt: string;
  name?: string;
}

export interface UserProfile extends User {
  phone?: string;
  avatarUrl?: string;
  mfaEnabled: boolean;
  lastLogin?: string;
}

// Authentication types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  accessToken: string;
  refreshToken?: string;
  requiresMfa: boolean;
  mfaType?: MfaType;
}

export type MfaType = 'totp' | 'webauthn' | 'backup';

export interface MfaVerificationPayload {
  mfaType: MfaType;
  code?: string; // For TOTP
  credentialId?: string; // For WebAuthn
}

export interface VerificationResponse {
  accessToken: string;
  refreshToken?: string;
  user: User;
}

// Error handling
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

// Token types
export interface DecodedToken {
  sub: string;
  exp: number;
  iat: number;
  role: string;
  permissions: string[];
}

// RBAC types
export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  parentRole?: string;
}

export interface Permission {
  id: string;
  name: string;
  description: string;
  resource: string;
  action: 'create' | 'read' | 'update' | 'delete' | 'manage';
}

// Audit log types
export interface AuditLogEntry {
  id: string;
  userId: string;
  action: string;
  resource: string;
  timestamp: string;
  ipAddress: string;
  userAgent: string;
  geoLocation?: {
    country: string;
    city: string;
    coordinates: [number, number];
  };
}

// Theme
export type Theme = 'light' | 'dark' | 'system';