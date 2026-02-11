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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/81af291e-806e-4a0b-b546-57de6f51e153',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api/axios-config.ts:16',message:'Request interceptor - checking token',data:{url:config.url,hasToken:!!token,tokenPreview:token?.substring(0,20)+'...',hasAuthHeader:!!config.headers.Authorization},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
    // #endregion
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/81af291e-806e-4a0b-b546-57de6f51e153',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api/axios-config.ts:19',message:'Token added to header',data:{authHeaderPreview:config.headers.Authorization?.substring(0,30)+'...'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
        // #endregion
    } else {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/81af291e-806e-4a0b-b546-57de6f51e153',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api/axios-config.ts:23',message:'No token found in localStorage',data:{localStorageKeys:Object.keys(localStorage)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
    }
    return config;
});

// Обрабатываем ошибки авторизации
axiosInstance.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/81af291e-806e-4a0b-b546-57de6f51e153',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api/axios-config.ts:28',message:'401 Unauthorized received',data:{url:error.config?.url,requestHeaders:error.config?.headers,responseData:error.response?.data,hasTokenBeforeClean:!!localStorage.getItem('access_token')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
            // #endregion
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
