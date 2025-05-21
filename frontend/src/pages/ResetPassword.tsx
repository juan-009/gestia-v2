import React, { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { Lock, ArrowLeft } from 'lucide-react';
import { useResetPasswordMutation } from '../features/auth/authApi';
import { addToast } from '../features/ui/uiSlice';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import Alert from '../components/ui/Alert';
import { validatePassword } from '../utils/validation';

const ResetPassword: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const [resetPassword] = useResetPasswordMutation();

  const [formData, setFormData] = useState({
    password: '',
    confirmPassword: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setErrors(prev => ({ ...prev, [name]: '' }));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!validatePassword(formData.password)) {
      newErrors.password = 'Password must be at least 8 characters with uppercase, lowercase, and numbers';
    }

    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsLoading(true);
    setError(null);

    try {
      await resetPassword({
        token: token || '',
        password: formData.password,
        confirmPassword: formData.confirmPassword,
      }).unwrap();

      dispatch(addToast({
        type: 'success',
        message: 'Password successfully reset! Please log in with your new password.',
      }));

      navigate('/auth/login');
    } catch (err) {
      console.error('Password reset error:', err);
      
      const errorMessage = typeof err === 'object' && err !== null && 'message' in err
        ? String(err.message)
        : 'Failed to reset password. Please try again.';
      
      setError(errorMessage);
      
      dispatch(addToast({
        type: 'error',
        message: errorMessage,
      }));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
      <div className="max-w-md w-full space-y-8 p-8 bg-white dark:bg-gray-800 rounded-lg shadow-md">
        <div className="text-center">
          <div className="flex justify-center">
            <div className="h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
              <Lock className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900 dark:text-white">
            Reset your password
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Please enter your new password
          </p>
        </div>

        {error && (
          <Alert variant="error" title="Password reset failed">
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <Input
            label="New Password"
            id="password"
            name="password"
            type="password"
            value={formData.password}
            onChange={handleChange}
            error={errors.password}
            required
            fullWidth
          />

          <Input
            label="Confirm New Password"
            id="confirmPassword"
            name="confirmPassword"
            type="password"
            value={formData.confirmPassword}
            onChange={handleChange}
            error={errors.confirmPassword}
            required
            fullWidth
          />

          <Button 
            type="submit" 
            fullWidth 
            isLoading={isLoading}
          >
            Reset Password
          </Button>

          <div className="text-center">
            <Button
              variant="link"
              onClick={() => navigate('/auth/login')}
              leftIcon={<ArrowLeft className="h-4 w-4" />}
            >
              Back to login
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ResetPassword;