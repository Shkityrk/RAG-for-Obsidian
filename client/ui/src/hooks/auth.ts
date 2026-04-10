import { useMutation } from '@tanstack/react-query';
import { authApi, RegisterRequest, LoginRequest } from '../api/auth';
import { saveToken, saveUserData, logout as logoutUtil } from '../utils/auth';
import { showSuccessNotification, showErrorNotification } from '../utils/error-notifications';

export const useRegister = () => {
  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (data) => {
      saveToken(data.access_token);
      saveUserData({ user_id: data.user.id, username: data.user.username });
      showSuccessNotification('Registration successful!');
      window.location.href = '/index';
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
      saveUserData({ user_id: data.user.id, username: data.user.username });
      showSuccessNotification('Login successful!');
      window.location.href = '/index';
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

