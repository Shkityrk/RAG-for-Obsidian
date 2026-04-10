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
    return {
        ...response.data,
        related_documents: response.data.related_documents || [],
        fragments: response.data.fragments || [],
    };
};

const cleanChatMessages = async (chatId: number) => {
    const response = await axiosInstance.delete<MessageResponse>(API_MESSAGES, {
        params: { chat_id: chatId }
    });
    return response.data;
};

const sendDeepResearchMessage = async (data: QueryRequest) => {
    const response = await axiosInstance.post<AnswerResponse>(`${API_MESSAGES}deep-research`, data);
    return {
        ...response.data,
        related_documents: response.data.related_documents || [],
        fragments: response.data.fragments || [],
    };
};


export {getChatMessages, sendChatMessage, cleanChatMessages, sendDeepResearchMessage};
