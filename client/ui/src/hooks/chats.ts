import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { chatsApi, CreateChatRequest, UpdateChatRequest } from '../api/chats';
import { showSuccessNotification, showErrorNotification } from '../utils/error-notifications';

const getErrorMessage = (error: unknown, fallback: string): string => {
  if (typeof error === 'object' && error !== null) {
    const maybeResponse = (error as { response?: { data?: { detail?: string } } }).response;
    if (maybeResponse?.data?.detail) {
      return maybeResponse.data.detail;
    }
    const maybeMessage = (error as { message?: string }).message;
    if (maybeMessage) {
      return maybeMessage;
    }
  }
  return fallback;
};

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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chats'] });
      showSuccessNotification('Chat created successfully!');
      // Не перенаправляем здесь - пусть компонент сам обработает
    },
    onError: (error: unknown) => {
      const message = getErrorMessage(error, 'Failed to create chat');
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
    onError: (error: unknown) => {
      const message = getErrorMessage(error, 'Failed to update chat');
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
    onError: (error: unknown) => {
      const message = getErrorMessage(error, 'Failed to delete chat');
      showErrorNotification(message);
    },
  });
};

