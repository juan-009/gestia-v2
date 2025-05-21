import React from 'react';
import { useSelector } from 'react-redux';
import { Navigate } from 'react-router-dom';
import { Shield } from 'lucide-react';
import MfaForm from '../components/auth/MfaForm';
import { selectIsAuthenticated, selectAuth } from '../features/auth/authSlice';

const MfaVerification: React.FC = () => {
  const isAuthenticated = useSelector(selectIsAuthenticated);
  const { requiresMfa } = useSelector(selectAuth);
  
  // Redirect if already authenticated
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  
  // Redirect to login if MFA is not required
  if (!requiresMfa) {
    return <Navigate to="/auth/login" replace />;
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
      <div className="max-w-md w-full space-y-8 p-8 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <div className="text-center">
          <div className="flex justify-center">
            <div className="h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
              <Shield className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900 dark:text-white">Two-Factor Authentication</h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Please complete the verification step to continue
          </p>
        </div>
        
        <MfaForm />
        
        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
                Additional security
              </span>
            </div>
          </div>
          
          <div className="mt-6">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Having trouble? Contact support at{' '}
              <a href="mailto:support@example.com" className="text-blue-600 dark:text-blue-400">
                support@example.com
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MfaVerification;