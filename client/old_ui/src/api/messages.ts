import axiosInstance from "./axios-config";
import {MessageResponse} from "../types/general"
import {QueryRequest, AnswerResponse, MessageHistoryResponse} from "../types/messages"


const API_MESSAGES = '/api/messages/';


const getChatMessages = async (chatId: number, offset = 0, limit = 100) => {
    const response = await axiosInstance.get<MessageHistoryResponse>(API_MESSAGES, {
        params: { chat_id: chatId, offset, limit }
    });
    return response.data;
};


const sendChatMessage = async (data: QueryRequest) => {
    const response = await axiosInstance.post<AnswerResponse>(API_MESSAGES, data);
    console.log('=== API Response ===');
    console.log('Full response object:', response);
    console.log('Response data:', response.data);
    console.log('Response data keys:', Object.keys(response.data));
    console.log('Fragments in response.data:', response.data.fragments);
    console.log('Fragments type:', typeof response.data.fragments);
    console.log('Fragments length:', response.data.fragments?.length);
    console.log('Full response JSON:', JSON.stringify(response.data, null, 2));
    return response.data;
};

const cleanChatMessages = async (chatId: number) => {
    const response = await axiosInstance.delete<MessageResponse>(API_MESSAGES, {
        params: { chat_id: chatId }
    });
    return response.data;
};

const sendCombinedSearchMessage = async (data: QueryRequest) => {
    const response = await axiosInstance.post<AnswerResponse>(`${API_MESSAGES}combined`, data);
    console.log('=== Combined Search API Response ===');
    console.log('Full response object:', response);
    console.log('Response data:', response.data);
    return response.data;
};


export {getChatMessages, sendChatMessage, cleanChatMessages, sendCombinedSearchMessage};