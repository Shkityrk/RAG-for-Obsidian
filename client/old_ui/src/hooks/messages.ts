import { getChatMessages, sendChatMessage, cleanChatMessages, sendCombinedSearchMessage } from "../api/messages";
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import { QueryRequest } from "../types/messages";
import handleAPIError from "../utils/error-notifications";


const useChatMessages = (chatId: number | null) => {
    return useQuery(
        {
            queryKey: ["chat_messages", chatId],
            queryFn: () => getChatMessages(chatId!),
            enabled: !!chatId,
            staleTime: 1000 * 60 * 10,
        }
    )
};

const useSendChatMessage = () => {
    const queryClient = useQueryClient();
    return useMutation(
        {
            mutationKey: ["send_chat_messages"],
            mutationFn: (data: QueryRequest) => sendChatMessage(data),
            onError: handleAPIError,
            onSuccess: (_, variables) => {
                queryClient.invalidateQueries({ queryKey: ["chat_messages", variables.chat_id] });
                queryClient.invalidateQueries({ queryKey: ["llm_tokens"] });
                queryClient.invalidateQueries({ queryKey: ["chats"] });
            },
        }
    )
};

const useCleanChatMessage = () => {
    const queryClient = useQueryClient();
    return useMutation(
        {
            mutationKey: ["clean_chat_messages"],
            mutationFn: (chatId: number) => cleanChatMessages(chatId),
            onError: handleAPIError,
            onSuccess: (_, chatId) => {
                queryClient.invalidateQueries({ queryKey: ["chat_messages", chatId] });
                queryClient.invalidateQueries({ queryKey: ["llm_tokens"] });
            },
        }
    )
};

const useSendCombinedSearchMessage = () => {
    const queryClient = useQueryClient();
    return useMutation(
        {
            mutationKey: ["send_combined_search_message"],
            mutationFn: (data: QueryRequest) => sendCombinedSearchMessage(data),
            onError: handleAPIError,
            onSuccess: (_, variables) => {
                queryClient.invalidateQueries({ queryKey: ["chat_messages", variables.chat_id] });
                queryClient.invalidateQueries({ queryKey: ["llm_tokens"] });
                queryClient.invalidateQueries({ queryKey: ["chats"] });
            },
        }
    )
};

export {useChatMessages, useSendChatMessage, useCleanChatMessage, useSendCombinedSearchMessage};