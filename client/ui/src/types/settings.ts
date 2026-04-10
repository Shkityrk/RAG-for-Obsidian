interface LLMSettingsRequest {
    openrouter_api_key: string;
    openrouter_llm_model: string;
    openrouter_deep_research_model: string;
    temperature: number;
    top_p: number;
    presence_penalty: number;
    frequency_penalty: number;
    max_tokens: number;
    deep_research_temperature: number;
    deep_research_top_p: number;
    deep_research_presence_penalty: number;
    deep_research_frequency_penalty: number;
    deep_research_max_tokens: number;
}

type LLMSettingsResponse = LLMSettingsRequest;

interface LLMAvailabilityResponse {
    is_available: boolean;
    error_message: string;
}

export type {LLMSettingsRequest, LLMSettingsResponse, LLMAvailabilityResponse};
