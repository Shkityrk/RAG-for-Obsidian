import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { vaultsApi } from '../api/vaults';
import { showSuccessNotification, showErrorNotification } from '../utils/error-notifications';

const getErrorDetail = (error: unknown, fallback: string) => {
  const axiosError = error as AxiosError<{ detail?: string }>;
  return axiosError.response?.data?.detail || fallback;
};

export const useVaults = () => {
  return useQuery({
    queryKey: ['vaults'],
    queryFn: () => vaultsApi.list(),
    staleTime: 1000 * 60 * 5,
  });
};

export const useVault = (vaultId: number | null) => {
  return useQuery({
    queryKey: ['vault', vaultId],
    queryFn: () => vaultsApi.get(vaultId!),
    enabled: !!vaultId,
    staleTime: 1000 * 60 * 5,
  });
};

export const useUploadVault = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => vaultsApi.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vaults'] });
      showSuccessNotification('Vault успешно загружен');
    },
    onError: (error: unknown) => {
      const message = getErrorDetail(error, 'Не удалось загрузить vault');
      showErrorNotification(message);
    },
  });
};

export const useDeleteVault = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vaultId: number) => vaultsApi.delete(vaultId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vaults'] });
      showSuccessNotification('Vault успешно удален');
    },
    onError: (error: unknown) => {
      const message = getErrorDetail(error, 'Не удалось удалить vault');
      showErrorNotification(message);
    },
  });
};

