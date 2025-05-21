import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { Eye, EyeOff, Mail, Lock } from 'lucide-react';
import Input from '../ui/Input';
import Button from '../ui/Button';
import Alert from '../ui/Alert';
import { useLoginMutation } from '../../features/auth/authApi';
import { loginStart, loginSuccess, loginFailure } from '../../features/auth/authSlice';
import { addToast } from '../../features/ui/uiSlice';
import { LoginResponse } from '../../types';
import { validateEmail } from '../../utils/validation';

const LoginForm: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [login] = useLoginMutation();
  
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  
  const validate = (): boolean => {
    const newErrors: { email?: string; password?: string } = {};
    
    if (!email) {
      newErrors.email = 'Email is required';
    } else if (!validateEmail(email)) {
      newErrors.email = 'Please enter a valid email address';
    }
    
    if (!password) {
      newErrors.password = 'Password is required';
    } else if (password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validate()) return;
    
    try {
      dispatch(loginStart());
      const response = await login({ email, password }).unwrap();
      dispatch(loginSuccess(response));
      
      if (response.requiresMfa) {
        // Redirect to MFA verification
        navigate('/auth/mfa-verification');
      } else {
        // Redirect to dashboard
        navigate('/dashboard');
        dispatch(addToast({
          type: 'success',
          message: 'Successfully logged in!',
        }));
      }
    } catch (error) {
      console.error('Login error:', error);
      const errorMessage = typeof error === 'object' && error !== null && 'message' in error
        ? String(error.message)
        : 'Failed to login. Please check your credentials.';
        
      dispatch(loginFailure(errorMessage));
      
      dispatch(addToast({
        type: 'error',
        message: errorMessage,
      }));
    }
  };
  
  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Input
        label="Email Address"
        type="email"
        id="email"
        name="email"
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={errors.email}
        fullWidth
        leftAddon={<Mail className="h-5 w-5" />}
        required
      />
      
      <Input
        label="Password"
        type={showPassword ? 'text' : 'password'}
        id="password"
        name="password"
        autoComplete="current-password"
        placeholder="••••••••"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={errors.password}
        fullWidth
        leftAddon={<Lock className="h-5 w-5" />}
        rightAddon={
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="focus:outline-none"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? (
              <EyeOff className="h-5 w-5" />
            ) : (
              <Eye className="h-5 w-5" />
            )}
          </button>
        }
        required
      />
      
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <input
            id="remember-me"
            name="remember-me"
            type="checkbox"
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label
            htmlFor="remember-me"
            className="ml-2 block text-sm text-gray-700 dark:text-gray-300"
          >
            Remember me
          </label>
        </div>
        
        <div className="text-sm">
          <a
            href="/auth/forgot-password"
            className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
          >
            Forgot your password?
          </a>
        </div>
      </div>
      
      <Button type="submit" fullWidth isLoading={false}>
        Sign in
      </Button>
    </form>
  );
};

export default LoginForm;