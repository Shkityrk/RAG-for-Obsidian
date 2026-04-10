import axiosInstance from './axios-config';

export interface Chat {
  id: number;
  user_id: number;
  vault_id: number | null;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatListResponse {
  chats: Chat[];
}

export interface CreateChatRequest {
  vault_id?: number | null;
  title?: string;
}

export interface UpdateChatRequest {
  title: string;
}

export const chatsApi = {
  list: async (): Promise<ChatListResponse> => {
    const response = await axiosInstance.get<ChatListResponse>('/api/chats/');
    return response.data;
  },

  get: async (chatId: number): Promise<Chat> => {
    const response = await axiosInstance.get<Chat>(`/api/chats/${chatId}`);
    return response.data;
  },

  create: async (data: CreateChatRequest): Promise<Chat> => {
    const response = await axiosInstance.post<Chat>('/api/chats/', data);
    return response.data;
  },

  update: async (chatId: number, data: UpdateChatRequest): Promise<Chat> => {
    const response = await axiosInstance.put<Chat>(`/api/chats/${chatId}`, data);
    return response.data;
  },

  delete: async (chatId: number): Promise<{ message: string }> => {
    const response = await axiosInstance.delete<{ message: string }>(`/api/chats/${chatId}`);
    return response.data;
  },
};

