import { useMutation } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { authApi, RegisterRequest, LoginRequest } from '../api/auth';
import { saveToken, saveUserData, logout as logoutUtil } from '../utils/auth';
import { showSuccessNotification, showErrorNotification } from '../utils/error-notifications';

const getErrorDetail = (error: unknown, fallback: string) => {
  const axiosError = error as AxiosError<{ detail?: string }>;
  return axiosError.response?.data?.detail || fallback;
};

export const useRegister = () => {
  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (data) => {
      saveToken(data.access_token);
      saveUserData({ user_id: data.user.id, username: data.user.username });
      showSuccessNotification('Регистрация прошла успешно');
      window.location.href = '/index';
    },
    onError: (error: unknown) => {
      const message = getErrorDetail(error, 'Не удалось зарегистрироваться');
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
      showSuccessNotification('Вход выполнен');
      window.location.href = '/index';
    },
    onError: (error: unknown) => {
      const message = getErrorDetail(error, 'Не удалось войти');
      showErrorNotification(message);
    },
  });
};

export const logout = () => {
  logoutUtil();
};

