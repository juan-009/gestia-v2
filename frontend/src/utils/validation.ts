import validator from 'validator';
import { z } from 'zod';

// Name validation
export const validateName = (name: string): boolean => {
  return name.trim().length > 0 && /^[a-zA-Z\s-']+$/.test(name);
};

// Email validation
export const validateEmail = (email: string): boolean => {
  return validator.isEmail(email);
};

// Password strength validation
export const validatePassword = (password: string): boolean => {
  // Minimum 8 characters, at least one uppercase letter, one lowercase letter, and one number
  return validator.isStrongPassword(password, {
    minLength: 8,
    minLowercase: 1,
    minUppercase: 1,
    minNumbers: 1,
    minSymbols: 0,
  });
};

// Phone number validation
export const validatePhone = (phone: string): boolean => {
  return validator.isMobilePhone(phone);
};

// Zod schemas for form validation

// Login schema
export const loginSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email address' }),
  password: z.string().min(8, { message: 'Password must be at least 8 characters' }),
});

// Registration schema
export const registrationSchema = z.object({
  email: z.string().email({ message: 'Please enter a valid email address' }),
  password: z
    .string()
    .min(8, { message: 'Password must be at least 8 characters' })
    .regex(/[A-Z]/, { message: 'Password must contain at least one uppercase letter' })
    .regex(/[a-z]/, { message: 'Password must contain at least one lowercase letter' })
    .regex(/[0-9]/, { message: 'Password must contain at least one number' }),
  confirmPassword: z.string(),
  firstName: z.string().min(1, { message: 'First name is required' }),
  lastName: z.string().min(1, { message: 'Last name is required' }),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

// Profile update schema
export const profileUpdateSchema = z.object({
  firstName: z.string().min(1, { message: 'First name is required' }),
  lastName: z.string().min(1, { message: 'Last name is required' }),
  email: z.string().email({ message: 'Please enter a valid email address' }),
  phone: z.string().optional().refine(
    (val) => !val || validatePhone(val),
    { message: 'Please enter a valid phone number' }
  ),
});

// Password change schema
export const passwordChangeSchema = z.object({
  currentPassword: z.string().min(1, { message: 'Current password is required' }),
  newPassword: z
    .string()
    .min(8, { message: 'Password must be at least 8 characters' })
    .regex(/[A-Z]/, { message: 'Password must contain at least one uppercase letter' })
    .regex(/[a-z]/, { message: 'Password must contain at least one lowercase letter' })
    .regex(/[0-9]/, { message: 'Password must contain at least one number' }),
  confirmPassword: z.string(),
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

// MFA verification schema
export const mfaVerificationSchema = z.object({
  code: z.string().regex(/^\d{6}$/, { message: 'Code must be 6 digits' }),
});

// Role creation schema
export const roleSchema = z.object({
  name: z.string().min(1, { message: 'Role name is required' }),
  description: z.string().optional(),
  permissions: z.array(z.string()).min(1, { message: 'At least one permission is required' }),
  parentRole: z.string().optional(),
});