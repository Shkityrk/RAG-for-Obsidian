import axios from 'axios';
import { getToken } from '../utils/auth';

const MODE = import.meta.env.VITE_APPLICATION_MODE;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const axiosInstance = axios.create({
    baseURL: MODE === "dev"? API_BASE_URL: undefined,
    withCredentials: false,
    timeout: 600000, // 10 минут в миллисекундах
});

axiosInstance.defaults.headers.common['Content-Type'] = 'application/json';

// Добавляем токен в заголовки для всех запросов
axiosInstance.interceptors.request.use((config) => {
    const token = getToken();
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Обрабатываем ошибки авторизации
axiosInstance.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // Токен недействителен или отсутствует - перенаправляем на логин
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_data');
            if (window.location.pathname !== '/auth') {
                window.location.href = '/auth';
            }
        }
        return Promise.reject(error);
    }
);

export default axiosInstance;
