import { http, HttpResponse } from 'msw'
import { SignJWT } from 'jose';

// Types for request bodies
interface LoginRequest {
  email: string;
  password: string;
}

interface MfaVerifyRequest {
  code: string;
  mfaType?: 'totp' | 'webauthn' | 'backup';
}

interface RegisterRequest {
  email: string;
  firstName: string;
  lastName: string;
  password: string;
}

interface PasswordResetRequest {
  token: string;
  password: string;
}

// Mock data
const users = [
  {
    id: '1',
    email: 'admin@example.com',
    firstName: 'Admin',
    lastName: 'User',
    role: 'admin',
    permissions: ['manage_users', 'manage_roles', 'view_audit_logs'],
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
    mfaEnabled: true,
    mfaType: 'totp',
  },
  {
    id: '2',
    email: 'user@example.com',
    firstName: 'Regular',
    lastName: 'User',
    role: 'user',
    permissions: ['view_profile'],
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
    mfaEnabled: false,
  },
] as const;

const roles = [
  {
    id: '1',
    name: 'Admin',
    description: 'Full system access',
    permissions: ['manage_users', 'manage_roles', 'view_audit_logs'],
  },
  {
    id: '2',
    name: 'User',
    description: 'Basic user access',
    permissions: ['view_profile'],
  },
] as const;

const auditLogs = [
  {
    id: '1',
    userId: '1',
    action: 'USER_LOGIN',
    resource: 'auth',
    timestamp: new Date().toISOString(),
    ipAddress: '192.168.1.1',
    userAgent: 'Mozilla/5.0',
    geoLocation: {
      country: 'United States',
      city: 'San Francisco',
      coordinates: [37.7749, -122.4194],
    },
  },
  {
    id: '2',
    userId: '1',
    action: 'PROFILE_UPDATE',
    resource: 'user',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    ipAddress: '192.168.1.1',
    userAgent: 'Mozilla/5.0',
    geoLocation: {
      country: 'United States',
      city: 'San Francisco',
      coordinates: [37.7749, -122.4194],
    },
  },
  {
    id: '3',
    userId: '2',
    action: 'USER_LOGIN',
    resource: 'auth',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    ipAddress: '192.168.1.2',
    userAgent: 'Mozilla/5.0',
    geoLocation: {
      country: 'United States',
      city: 'New York',
      coordinates: [40.7128, -74.0060],
    },
  },
] as const;

// Helper function to generate JWT tokens
const generateToken = async (user: typeof users[number]) => {
  const secret = new TextEncoder().encode('your-secret-key');
  const token = await new SignJWT({
    sub: user.id,
    role: user.role,
    permissions: user.permissions,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('2h')
    .sign(secret);
  return token;
};

// API handlers
export const handlers = [
  // Auth endpoints
  http.post('/auth/login', async ({ request }) => {
    const { email, password } = await request.json() as LoginRequest;
    const user = users.find(u => u.email === email);

    if (!user || password !== 'password123') {
      return HttpResponse.json(
        { message: 'Invalid credentials' },
        { status: 401 }
      );
    }

    const accessToken = await generateToken(user);

    if (user.mfaEnabled) {
      return HttpResponse.json({
        requiresMfa: true,
        mfaType: user.mfaType,
        accessToken,
      });
    }

    return HttpResponse.json({
      accessToken,
      requiresMfa: false,
      user,
    });
  }),

  http.post('/auth/mfa/verify', async ({ request }) => {
    const { code } = await request.json() as MfaVerifyRequest;
    
    // Simulate verification (accept any 6-digit code)
    if (!/^\d{6}$/.test(code)) {
      return HttpResponse.json(
        { message: 'Invalid verification code' },
        { status: 400 }
      );
    }

    const user = users[0]; // Use admin user for demo
    const accessToken = await generateToken(user);

    return HttpResponse.json({
      accessToken,
      user,
    });
  }),

  http.post('/auth/register', async ({ request }) => {
    const data = await request.json() as RegisterRequest;
    
    // Check if email already exists
    if (users.some(u => u.email === data.email)) {
      return HttpResponse.json(
        { message: 'Email already registered' },
        { status: 400 }
      );
    }
    
    const newUser = {
      id: String(users.length + 1),
      email: data.email,
      firstName: data.firstName,
      lastName: data.lastName,
      role: 'user' as const,
      permissions: ['view_profile'] as const,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      mfaEnabled: false,
    };
    
    return HttpResponse.json(newUser);
  }),

  // User endpoints
  http.get('/auth/me', ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }
    return HttpResponse.json(users[0]);
  }),

  http.get('/auth/me/profile', ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }
    
    const profile = {
      ...users[0],
      phone: '+1234567890',
      avatarUrl: 'https://i.pravatar.cc/150?u=admin',
      lastLogin: new Date().toISOString(),
    };
    return HttpResponse.json(profile);
  }),

  http.patch('/auth/me/profile', async ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }
    
    const updates = await request.json() as Partial<typeof users[number]>;
    const updatedUser = { ...users[0], ...updates };
    return HttpResponse.json(updatedUser);
  }),

  // Role management
  http.get('/auth/admin/roles', ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }
    return HttpResponse.json(roles);
  }),

  http.post('/auth/admin/roles', async ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }
    
    const newRole = await request.json() as Omit<typeof roles[number], 'id'>;
    const role = { id: String(roles.length + 1), ...newRole };
    return HttpResponse.json(role);
  }),

  // Audit logs
  http.get('/auth/admin/audit-logs', ({ request }) => {
    const authHeader = request.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return HttpResponse.json(
        { message: 'Unauthorized' },
        { status: 401 }
      );
    }
    
    const url = new URL(request.url);
    const page = Number(url.searchParams.get('page')) || 1;
    const limit = Number(url.searchParams.get('limit')) || 10;
    
    const paginatedLogs = auditLogs.slice((page - 1) * limit, page * limit);
    return HttpResponse.json({
      logs: paginatedLogs,
      total: auditLogs.length,
      page,
      limit,
    });
  }),

  // Password recovery
  http.post('/auth/password/recovery', async ({ request }) => {
    await request.json() as { email: string };
    // Always return success to prevent email enumeration
    return HttpResponse.json({
      message: 'If an account exists with this email, you will receive recovery instructions.',
    });
  }),

  http.post('/auth/password/reset', async ({ request }) => {
    const { token, password } = await request.json() as PasswordResetRequest;
    
    if (!token || !password) {
      return HttpResponse.json(
        { message: 'Invalid token or password' },
        { status: 400 }
      );
    }
    
    return HttpResponse.json({
      message: 'Password successfully reset.',
    });
  }),
];