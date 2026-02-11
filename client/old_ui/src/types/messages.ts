type RoleType = "user" | "assistant";

interface MessageSchema  {
    id: string | number;
    chat_id?: number;
    role: RoleType;
    content: string;
    created_date?: string;
    datetime?: string;
    fragments?: FragmentInfo[];
}

interface MessageHistoryResponse {
    messages: MessageSchema[];
}

interface QueryRequest {
    content: string;
    chat_id: number;
    vault_id: number;
}

interface FragmentInfo {
    filename: string;
    text: string;
    similarity: number;
    chunk_id: number | null;
}

interface AnswerResponse {
    answer: string;
    related_documents: string[];
    fragments: FragmentInfo[];
    message_id: number;
}
  



export type { MessageSchema, MessageHistoryResponse, QueryRequest, AnswerResponse, FragmentInfo };
