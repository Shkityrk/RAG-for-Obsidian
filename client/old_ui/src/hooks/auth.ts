import { useMutation } from '@tanstack/react-query';
import { authApi, RegisterRequest, LoginRequest } from '../api/auth';
import { saveToken, saveUserData, logout as logoutUtil } from '../utils/auth';
import { showSuccessNotification, showErrorNotification } from '../utils/error-notifications';

export const useRegister = () => {
  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (data) => {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/81af291e-806e-4a0b-b546-57de6f51e153',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'hooks/auth.ts:10',message:'Registration success - saving token',data:{hasToken:!!data.access_token,tokenLength:data.access_token?.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      saveToken(data.access_token);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/81af291e-806e-4a0b-b546-57de6f51e153',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'hooks/auth.ts:12',message:'Token saved - checking localStorage',data:{storedToken:localStorage.getItem('access_token')?.substring(0,20)+'...'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
      // #endregion
      saveUserData({ user_id: data.user_id, username: data.username });
      showSuccessNotification('Registration successful!');
      window.location.href = '/';
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Registration failed';
      showErrorNotification(message);
    },
  });
};

export const useLogin = () => {
  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (data) => {
      saveToken(data.access_token);
      saveUserData({ user_id: data.user_id, username: data.username });
      showSuccessNotification('Login successful!');
      window.location.href = '/';
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Login failed';
      showErrorNotification(message);
    },
  });
};

export const logout = () => {
  logoutUtil();
};

