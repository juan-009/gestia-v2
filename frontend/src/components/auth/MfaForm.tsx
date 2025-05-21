import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import Input from '../ui/Input';
import Button from '../ui/Button';
import Alert from '../ui/Alert';
import { useVerifyMfaMutation } from '../../features/auth/authApi';
import { mfaVerificationSuccess, mfaVerificationFailure, selectAuth } from '../../features/auth/authSlice';
import { addToast } from '../../features/ui/uiSlice';
import { MfaType } from '../../types';

const MfaForm: React.FC = () => {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { mfaType } = useSelector(selectAuth);
  const [verifyMfa] = useVerifyMfaMutation();
  
  const [code, setCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState(30);
  
  // Countdown timer for TOTP codes
  useEffect(() => {
    if (mfaType === 'totp') {
      const interval = setInterval(() => {
        setTimeRemaining((prev) => {
          if (prev <= 1) {
            // Reset to 30 seconds when it hits 0
            return 30;
          }
          return prev - 1;
        });
      }, 1000);
      
      return () => clearInterval(interval);
    }
  }, [mfaType]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!code.trim()) {
      setError('Please enter your verification code');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await verifyMfa({
        mfaType: mfaType as MfaType,
        code,
      }).unwrap();
      
      dispatch(mfaVerificationSuccess(response));
      navigate('/dashboard');
      
      dispatch(addToast({
        type: 'success',
        message: 'Successfully verified!',
      }));
    } catch (error) {
      console.error('MFA verification error:', error);
      const errorMessage = typeof error === 'object' && error !== null && 'message' in error
        ? String(error.message)
        : 'Failed to verify your code. Please try again.';
        
      dispatch(mfaVerificationFailure(errorMessage));
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleWebAuthnVerification = async () => {
    if (mfaType !== 'webauthn') return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      // Check if the WebAuthn API is available
      if (!window.PublicKeyCredential) {
        throw new Error('WebAuthn is not supported by this browser');
      }
      
      // In a real app, you would get the challenge from the server
      // and use navigator.credentials.get() to verify
      
      // This is a placeholder for WebAuthn verification
      const response = await verifyMfa({
        mfaType: 'webauthn',
      }).unwrap();
      
      dispatch(mfaVerificationSuccess(response));
      navigate('/dashboard');
      
      dispatch(addToast({
        type: 'success',
        message: 'Successfully verified!',
      }));
    } catch (error) {
      console.error('WebAuthn verification error:', error);
      const errorMessage = typeof error === 'object' && error !== null && 'message' in error
        ? String(error.message)
        : 'Failed to verify with your security key. Please try again.';
        
      dispatch(mfaVerificationFailure(errorMessage));
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleBackupCodeVerification = async () => {
    if (mfaType !== 'backup') return;
    
    // Implementation for backup code verification
    // Similar to TOTP verification but with different validation
  };
  
  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="error" title="Verification failed">
          {error}
        </Alert>
      )}
      
      {mfaType === 'totp' && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Two-Factor Authentication</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Enter the 6-digit code from your authenticator app.
            </p>
            
            <div className="flex items-center justify-between">
              <Input
                label="Verification Code"
                type="text"
                id="code"
                name="code"
                placeholder="123456"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                autoComplete="one-time-code"
                maxLength={6}
                pattern="[0-9]{6}"
                inputMode="numeric"
                fullWidth
              />
              
              <div className="ml-4 flex items-center justify-center w-10 h-10 rounded-full bg-gray-100 dark:bg-gray-800">
                <span className="text-sm font-medium">{timeRemaining}</span>
              </div>
            </div>
          </div>
          
          <Button type="submit" fullWidth isLoading={isLoading}>
            Verify
          </Button>
          
          <div className="text-center">
            <a
              href="#backup-code"
              className="text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
              onClick={(e) => {
                e.preventDefault();
                // Logic to switch to backup code verification
              }}
            >
              Use backup code
            </a>
          </div>
        </form>
      )}
      
      {mfaType === 'webauthn' && (
        <div className="space-y-6">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Security Key Verification</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Use your security key or biometric authentication to verify your identity.
            </p>
          </div>
          
          <Button onClick={handleWebAuthnVerification} fullWidth isLoading={isLoading}>
            Verify with Security Key
          </Button>
          
          <div className="text-center">
            <a
              href="#backup-code"
              className="text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
              onClick={(e) => {
                e.preventDefault();
                // Logic to switch to backup code verification
              }}
            >
              Use backup code
            </a>
          </div>
        </div>
      )}
      
      {mfaType === 'backup' && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Backup Code Verification</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Enter one of your backup codes. Each code can only be used once.
            </p>
            
            <Input
              label="Backup Code"
              type="text"
              id="code"
              name="code"
              placeholder="XXXX-XXXX-XXXX"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              fullWidth
            />
          </div>
          
          <Button type="submit" fullWidth isLoading={isLoading}>
            Verify
          </Button>
        </form>
      )}
    </div>
  );
};

export default MfaForm;