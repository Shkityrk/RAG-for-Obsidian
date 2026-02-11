const TOKEN_KEY = 'access_token';
const USER_KEY = 'user_data';

export interface UserData {
  user_id: number;
  username: string;
}

export const saveToken = (token: string) => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const removeToken = () => {
  localStorage.removeItem(TOKEN_KEY);
};

export const saveUserData = (userData: UserData) => {
  localStorage.setItem(USER_KEY, JSON.stringify(userData));
};

export const getUserData = (): UserData | null => {
  const data = localStorage.getItem(USER_KEY);
  if (data) {
    try {
      return JSON.parse(data) as UserData;
    } catch {
      return null;
    }
  }
  return null;
};

export const removeUserData = () => {
  localStorage.removeItem(USER_KEY);
};

export const isAuthenticated = (): boolean => {
  return !!getToken();
};

export const logout = () => {
  removeToken();
  removeUserData();
  window.location.href = '/auth';
};

