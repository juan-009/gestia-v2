import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { 
  useGetUserProfileQuery,
  useUpdateUserProfileMutation 
} from '../features/user/userApi';
import { 
  User,
  Mail,
  Phone,
  Shield,
  Key,
  AlertCircle
} from 'lucide-react';
import Input from '../components/ui/Input';
import Button from '../components/ui/Button';
import Alert from '../components/ui/Alert';
import { addToast } from '../features/ui/uiSlice';
import { validateEmail, validatePhone } from '../utils/validation';

const Profile: React.FC = () => {
  const dispatch = useDispatch();
  const { data: profile, isLoading: isLoadingProfile } = useGetUserProfileQuery();
  const [updateProfile, { isLoading: isUpdating }] = useUpdateUserProfileMutation();

  const [formData, setFormData] = useState({
    firstName: profile?.firstName || '',
    lastName: profile?.lastName || '',
    email: profile?.email || '',
    phone: profile?.phone || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  React.useEffect(() => {
    if (profile) {
      setFormData({
        firstName: profile.firstName,
        lastName: profile.lastName,
        email: profile.email,
        phone: profile.phone || '',
      });
    }
  }, [profile]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required';
    }

    if (!formData.lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    }

    if (!validateEmail(formData.email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    if (formData.phone && !validatePhone(formData.phone)) {
      newErrors.phone = 'Please enter a valid phone number';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    try {
      await updateProfile(formData).unwrap();
      
      dispatch(addToast({
        type: 'success',
        message: 'Profile updated successfully',
      }));
    } catch (error) {
      console.error('Failed to update profile:', error);
      
      dispatch(addToast({
        type: 'error',
        message: 'Failed to update profile. Please try again.',
      }));
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  if (isLoadingProfile) {
    return (
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Profile Settings</h2>
        </div>

        <div className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input
                label="First Name"
                id="firstName"
                name="firstName"
                value={formData.firstName}
                onChange={handleChange}
                error={errors.firstName}
                leftAddon={<User className="h-5 w-5" />}
                required
              />

              <Input
                label="Last Name"
                id="lastName"
                name="lastName"
                value={formData.lastName}
                onChange={handleChange}
                error={errors.lastName}
                leftAddon={<User className="h-5 w-5" />}
                required
              />
            </div>

            <Input
              label="Email Address"
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              error={errors.email}
              leftAddon={<Mail className="h-5 w-5" />}
              required
            />

            <Input
              label="Phone Number"
              id="phone"
              name="phone"
              type="tel"
              value={formData.phone}
              onChange={handleChange}
              error={errors.phone}
              leftAddon={<Phone className="h-5 w-5" />}
              helperText="Optional"
            />

            <div className="flex justify-end space-x-4">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setFormData({
                  firstName: profile?.firstName || '',
                  lastName: profile?.lastName || '',
                  email: profile?.email || '',
                  phone: profile?.phone || '',
                })}
              >
                Reset
              </Button>
              <Button
                type="submit"
                isLoading={isUpdating}
              >
                Save Changes
              </Button>
            </div>
          </form>
        </div>
      </div>

      <div className="mt-6 bg-white dark:bg-gray-800 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Security</h2>
        </div>

        <div className="p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="h-5 w-5 text-gray-400" />
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Two-Factor Authentication
                </h3>
                <p className="text-sm text-gray-500">
                  {profile?.mfaEnabled 
                    ? 'Your account is protected by two-factor authentication' 
                    : 'Add additional security to your account'}
                </p>
              </div>
            </div>
            <Button variant={profile?.mfaEnabled ? 'secondary' : 'primary'}>
              {profile?.mfaEnabled ? 'Manage 2FA' : 'Enable 2FA'}
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Key className="h-5 w-5 text-gray-400" />
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Password
                </h3>
                <p className="text-sm text-gray-500">
                  Last changed {profile?.updatedAt ? new Date(profile.updatedAt).toLocaleDateString() : 'never'}
                </p>
              </div>
            </div>
            <Button>Change Password</Button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertCircle className="h-5 w-5 text-gray-400" />
              <div>
                <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                  Account Activity
                </h3>
                <p className="text-sm text-gray-500">
                  View recent login activity and security events
                </p>
              </div>
            </div>
            <Button variant="secondary">View Activity</Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;