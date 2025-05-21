import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Helper to merge Tailwind CSS classes conditionally
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}