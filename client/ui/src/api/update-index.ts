import axiosInstance from "./axios-config";
import { 
    IndexInfoResponse, 
    ClustersResponse, 
    UpdateIndexProgressResponse
} from "../types/update-index";
import { MessageResponse } from "../types/general";


const API_INDEX_INFO = '/api/index/info/';
const API_INDEX_CLUSTERS = '/api/index/clusters';
const API_INDEX_UPDATE = '/api/index/';
const API_INDEX_PROGRESS = '/api/index/progress';


const getIndexInfo = async (vaultId: number): Promise<IndexInfoResponse> => {
    const response = await axiosInstance.get<IndexInfoResponse>(API_INDEX_INFO, {
        params: { vault_id: vaultId }
    });
    return response.data;
};

const getClusters = async (vaultId: number): Promise<ClustersResponse> => {
    const response = await axiosInstance.get<ClustersResponse>(API_INDEX_CLUSTERS, {
        params: { vault_id: vaultId }
    });
    return response.data;
};

const updateIndex = async (vaultId: number): Promise<MessageResponse> => {
    const response = await axiosInstance.put<MessageResponse>(API_INDEX_UPDATE, null, {
        params: { vault_id: vaultId }
    });
    return response.data;
};

const getIndexProgress = async (vaultId: number): Promise<UpdateIndexProgressResponse> => {
    const response = await axiosInstance.get<UpdateIndexProgressResponse>(API_INDEX_PROGRESS, {
        params: { vault_id: vaultId }
    });
    return response.data;
};

const deleteIndex = async (vaultId: number): Promise<MessageResponse> => {
    const response = await axiosInstance.delete<MessageResponse>(API_INDEX_UPDATE, {
        params: { vault_id: vaultId }
    });
    return response.data;
};

export { getIndexInfo, getClusters, updateIndex, getIndexProgress, deleteIndex };