import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { vaultsApi } from '../api/vaults';
import { showSuccessNotification, showErrorNotification } from '../utils/error-notifications';

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
      showSuccessNotification('Vault uploaded successfully!');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to upload vault';
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
      showSuccessNotification('Vault deleted successfully!');
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to delete vault';
      showErrorNotification(message);
    },
  });
};

