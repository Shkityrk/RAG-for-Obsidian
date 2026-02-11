import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatsApi, Chat, CreateChatRequest, UpdateChatRequest } from '../api/chats';
import { showSuccessNotification, showErrorNotification } from '../utils/error-notifications';

export const useChats = () => {
  return useQuery({
    queryKey: ['chats'],
    queryFn: () => chatsApi.list(),
    staleTime: 1000 * 60 * 5,
  });
};

export const useChat = (chatId: number | null) => {
  return useQuery({
    queryKey: ['chat', chatId],
    queryFn: () => chatsApi.get(chatId!),
    enabled: !!chatId,
    staleTime: 1000 * 60 * 5,
  });
};

export const useCreateChat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateChatRequest) => chatsApi.create(data),
    onSuccess: (chat: Chat) => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      showSuccessNotification('Chat created successfully!');
      window.location.href = `/chat?chat_id=${chat.id}`;
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to create chat';
      showErrorNotification(message);
    },
  });
};

export const useUpdateChat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ chatId, data }: { chatId: number; data: UpdateChatRequest }) =>
      chatsApi.update(chatId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      showSuccessNotification('Chat updated successfully!');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to update chat';
      showErrorNotification(message);
    },
  });
};

export const useDeleteChat = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (chatId: number) => chatsApi.delete(chatId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      showSuccessNotification('Chat deleted successfully!');
      window.location.href = '/';
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to delete chat';
      showErrorNotification(message);
    },
  });
};

