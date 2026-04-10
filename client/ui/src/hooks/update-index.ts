import { getIndexInfo, getClusters, updateIndex, getIndexProgress, deleteIndex } from "../api/update-index";
import { useMutation, useQuery, useQueryClient, keepPreviousData  } from "@tanstack/react-query";
import { MessageResponse } from "../types/general";
import handleAPIError from "../utils/error-notifications";
import notifySuccess from "../utils/success-notifications";

const useIndexInfo = (vaultId: number | null) => {
    return useQuery({
        queryKey: ["index_info", vaultId],
        queryFn: () => getIndexInfo(vaultId!),
        enabled: !!vaultId,
        staleTime: 1000 * 60 * 10,
    });
};

const useClusters = (vaultId: number | null) => {
    return useQuery({
        queryKey: ["index_clusters", vaultId],
        queryFn: () => getClusters(vaultId!),
        enabled: !!vaultId,
        staleTime: 1000 * 60 * 10,
    });
};

const useUpdateIndex = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationKey: ["update_index"],
        mutationFn: (vaultId: number) => updateIndex(vaultId),
        onError: handleAPIError,
        onSuccess: (data: MessageResponse, vaultId: number) => {
            queryClient.invalidateQueries({ queryKey: ["index_info", vaultId] });
            queryClient.invalidateQueries({ queryKey: ["index_clusters", vaultId] });
            queryClient.invalidateQueries({ queryKey: ["index_progress", vaultId] });
            notifySuccess(data.message);
        },
    });
};

const useIndexProgress = (vaultId: number | null, shouldFetch: boolean) => {
    return useQuery({
        queryKey: ["index_progress", vaultId],
        queryFn: () => getIndexProgress(vaultId!),
        enabled: !!vaultId && shouldFetch,
        staleTime: 1000 * 60 * 10,
        placeholderData: keepPreviousData,
        refetchInterval: shouldFetch ? 1000 : false
    });
};

const useDeleteIndex = () => {
    const queryClient = useQueryClient();
    return useMutation({
        mutationKey: ["delete_index"],
        mutationFn: (vaultId: number) => deleteIndex(vaultId),
        onError: handleAPIError,
        onSuccess: (data: MessageResponse, vaultId: number) => {
            queryClient.invalidateQueries({ queryKey: ["index_info", vaultId] });
            queryClient.invalidateQueries({ queryKey: ["index_clusters", vaultId] });
            queryClient.invalidateQueries({ queryKey: ["index_progress", vaultId] });
            notifySuccess(data.message);
        },
    });
};

// Экспорт хуков
export { useIndexInfo, useClusters, useUpdateIndex, useIndexProgress, useDeleteIndex };