import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { User, MfaType } from '../../types';
import { tokenService } from '../../services/tokenService';
import { RootState } from '../../store/store';

interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  error: string | null;
  requiresMfa: boolean;
  mfaType: MfaType | null;
  failedAttempts: number;
  lockoutTime: number | null;
}

const initialState: AuthState = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
  error: null,
  requiresMfa: false,
  mfaType: null,
  failedAttempts: 0,
  lockoutTime: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    loginSuccess: (state, action: PayloadAction<{ accessToken: string; requiresMfa: boolean; mfaType?: MfaType }>) => {
      state.isLoading = false;
      
      if (action.payload.requiresMfa) {
        // If MFA is required, set requiresMfa to true but don't set isAuthenticated yet
        state.requiresMfa = true;
        state.mfaType = action.payload.mfaType || 'totp';
      } else {
        // If MFA is not required, user is now authenticated
        state.isAuthenticated = true;
        tokenService.setAccessToken(action.payload.accessToken);
        
        // Extract user info from token
        const userInfo = tokenService.getUserFromToken();
        if (userInfo) {
          state.user = {
            id: userInfo.userId,
            role: userInfo.role,
            permissions: userInfo.permissions,
            email: '',  // Will be populated when user profile is fetched
            firstName: '',
            lastName: '',
            createdAt: '',
            updatedAt: ''
          };
        }
      }
      
      // Reset failed attempts
      state.failedAttempts = 0;
      state.lockoutTime = null;
    },
    loginFailure: (state, action: PayloadAction<string>) => {
      state.isLoading = false;
      state.error = action.payload;
      state.failedAttempts += 1;
      
      // Implement lockout after 5 failed attempts
      if (state.failedAttempts >= 5) {
        // Lock for 10 minutes
        state.lockoutTime = Date.now() + 10 * 60 * 1000;
      }
    },
    mfaVerificationSuccess: (state, action: PayloadAction<{ accessToken: string; user: User }>) => {
      state.isLoading = false;
      state.isAuthenticated = true;
      state.requiresMfa = false;
      state.mfaType = null;
      state.user = action.payload.user;
      tokenService.setAccessToken(action.payload.accessToken);
    },
    mfaVerificationFailure: (state, action: PayloadAction<string>) => {
      state.isLoading = false;
      state.error = action.payload;
    },
    logout: (state) => {
      state.isAuthenticated = false;
      state.user = null;
      state.requiresMfa = false;
      state.mfaType = null;
      tokenService.clearTokens();
    },
    clearError: (state) => {
      state.error = null;
    },
    updateUserInfo: (state, action: PayloadAction<Partial<User>>) => {
      if (state.user) {
        state.user = { ...state.user, ...action.payload };
      }
    },
  },
});

// Export actions
export const {
  loginStart,
  loginSuccess,
  loginFailure,
  mfaVerificationSuccess,
  mfaVerificationFailure,
  logout,
  clearError,
  updateUserInfo,
} = authSlice.actions;

// Selectors
export const selectAuth = (state: RootState) => state.auth;
export const selectUser = (state: RootState) => state.auth.user;
export const selectIsAuthenticated = (state: RootState) => state.auth.isAuthenticated;

export default authSlice.reducer;