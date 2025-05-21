import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { Mail, ArrowLeft } from 'lucide-react';
import { useRequestPasswordRecoveryMutation } from '../features/auth/authApi';
import { addToast } from '../features/ui/uiSlice';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import Alert from '../components/ui/Alert';
import { validateEmail } from '../utils/validation';

const ForgotPassword: React.FC = () => {
  const dispatch = useDispatch();
  const [requestPasswordRecovery] = useRequestPasswordRecoveryMutation();
  
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState<string | undefined>();
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value);
    setEmailError(undefined);
  };

  const validateForm = (): boolean => {
    if (!email || !validateEmail(email)) {
      setEmailError('Please enter a valid email address');
      return false;
    }
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      await requestPasswordRecovery({ email }).unwrap();
      setIsSubmitted(true);
      
      dispatch(addToast({
        type: 'success',
        message: 'Recovery instructions sent to your email',
      }));
    } catch (err) {
      console.error('Password recovery request error:', err);
      
      const errorMessage = typeof err === 'object' && err !== null && 'message' in err
        ? String(err.message)
        : 'Failed to process password recovery request. Please try again later.';
      
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
              <Mail className="h-6 w-6 text-blue-600 dark:text-blue-400" />
            </div>
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900 dark:text-white">
            Forgot your password?
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            {isSubmitted 
              ? "We've sent you an email with recovery instructions."
              : "Enter your email and we'll send you instructions to reset your password."}
          </p>
        </div>
        
        {error && (
          <Alert variant="error" title="Recovery request failed">
            {error}
          </Alert>
        )}
        
        {isSubmitted ? (
          <div className="space-y-6">
            <div className="rounded-md bg-green-50 dark:bg-green-900/30 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg 
                    className="h-5 w-5 text-green-400" 
                    xmlns="http://www.w3.org/2000/svg" 
                    viewBox="0 0 20 20" 
                    fill="currentColor" 
                    aria-hidden="true"
                  >
                    <path 
                      fillRule="evenodd" 
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" 
                      clipRule="evenodd" 
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-green-800 dark:text-green-200">
                    Please check your email for further instructions.
                  </p>
                </div>
              </div>
            </div>
            
            <Button 
              variant="secondary" 
              leftIcon={<ArrowLeft className="h-4 w-4" />}
              onClick={() => setIsSubmitted(false)}
            >
              Try another email
            </Button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            <div>
              <Input
                label="Email Address"
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={handleEmailChange}
                error={emailError}
                placeholder="you@example.com"
                leftAddon={<Mail className="h-5 w-5" />}
                required
                fullWidth
              />
            </div>
            
            <div>
              <Button 
                type="submit" 
                fullWidth 
                isLoading={isLoading}
              >
                Send recovery instructions
              </Button>
            </div>
          </form>
        )}
        
        <div className="mt-4 text-center">
          <Link 
            to="/auth/login" 
            className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
          >
            <div className="inline-flex items-center">
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to login
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;