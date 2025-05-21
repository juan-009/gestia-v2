import React from 'react';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { selectIsAuthenticated, selectAuth } from '../features/auth/authSlice';

// Layouts
import MainLayout from '../components/layout/MainLayout';
import AuthLayout from '../components/layout/AuthLayout';

// Pages
import Login from '../pages/Login';
import MfaVerification from '../pages/MfaVerification';
import Register from '../pages/Register';
import ForgotPassword from '../pages/ForgotPassword';
import ResetPassword from '../pages/ResetPassword';
import Dashboard from '../pages/Dashboard';
import Profile from '../pages/Profile';
import UserManagement from '../pages/UserManagement';
import AuditLogs from '../pages/AuditLogs';
import NotFound from '../pages/NotFound';

// Protected route component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useSelector(selectIsAuthenticated);
  
  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />;
  }
  
  return <>{children}</>;
};

// MFA required route
const MfaRequiredRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { requiresMfa } = useSelector(selectAuth);
  
  if (requiresMfa) {
    return <Navigate to="/auth/mfa-verification" replace />;
  }
  
  return <>{children}</>;
};

// Role-based route
const RoleRoute: React.FC<{ children: React.ReactNode; requiredRole: string }> = ({ 
  children, 
  requiredRole 
}) => {
  const { user } = useSelector(selectAuth);
  
  if (!user || user.role !== requiredRole) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

// Public route component (redirect if already authenticated)
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useSelector(selectIsAuthenticated);
  
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <>{children}</>;
};

// Router configuration
const Routes: React.FC = () => {
  const router = createBrowserRouter([
    {
      path: "/",
      element: <Navigate to="/dashboard" replace />,
    },
    {
      path: "/auth",
      element: <AuthLayout />,
      children: [
        {
          path: "login",
          element: (
            <PublicRoute>
              <Login />
            </PublicRoute>
          ),
        },
        {
          path: "mfa-verification",
          element: <MfaVerification />,
        },
        {
          path: "register",
          element: (
            <PublicRoute>
              <Register />
            </PublicRoute>
          ),
        },
        {
          path: "forgot-password",
          element: (
            <PublicRoute>
              <ForgotPassword />
            </PublicRoute>
          ),
        },
        {
          path: "reset-password/:token",
          element: (
            <PublicRoute>
              <ResetPassword />
            </PublicRoute>
          ),
        },
      ],
    },
    {
      path: "/",
      element: (
        <ProtectedRoute>
          <MfaRequiredRoute>
            <MainLayout />
          </MfaRequiredRoute>
        </ProtectedRoute>
      ),
      children: [
        {
          path: "dashboard",
          element: <Dashboard />,
        },
        {
          path: "profile",
          element: <Profile />,
        },
        {
          path: "users",
          element: (
            <RoleRoute requiredRole="admin">
              <UserManagement />
            </RoleRoute>
          ),
        },
        {
          path: "audit-logs",
          element: (
            <RoleRoute requiredRole="admin">
              <AuditLogs />
            </RoleRoute>
          ),
        },
      ],
    },
    {
      path: "*",
      element: <NotFound />,
    },
  ]);

  return <RouterProvider router={router} />;
};

export default Routes;