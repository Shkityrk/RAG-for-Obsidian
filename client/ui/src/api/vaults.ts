import axiosInstance from './axios-config';

export interface Vault {
  id: number;
  user_id: number;
  name: string;
  path: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface VaultListResponse {
  vaults: Vault[];
}

export interface VaultResponse {
  id: number;
  user_id: number;
  name: string;
  path: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export const vaultsApi = {
  list: async (): Promise<VaultListResponse> => {
    const response = await axiosInstance.get<VaultListResponse>('/api/vaults/');
    return response.data;
  },

  get: async (vaultId: number): Promise<VaultResponse> => {
    const response = await axiosInstance.get<VaultResponse>(`/api/vaults/${vaultId}`);
    return response.data;
  },

  upload: async (file: File): Promise<{ message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await axiosInstance.post<{ message: string }>('/api/vaults/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  delete: async (vaultId: number): Promise<{ message: string }> => {
    const response = await axiosInstance.delete<{ message: string }>(`/api/vaults/${vaultId}`);
    return response.data;
  },

  getFile: async (vaultId: number, filename: string): Promise<{ filename: string; content: string; path: string }> => {
    const response = await axiosInstance.get<{ filename: string; content: string; path: string }>(
      `/api/vaults/${vaultId}/file/${encodeURIComponent(filename)}`
    );
    return response.data;
  },
};

