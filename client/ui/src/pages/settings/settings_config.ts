import { LLMSettingsRequest } from "../../types/settings";

const DEFAULT_LLM_SETTINGS: LLMSettingsRequest = {
    openrouter_api_key: "",
    openrouter_llm_model: "google/gemini-3-flash-preview",
    openrouter_deep_research_model: "perplexity/sonar-deep-research",
    temperature: 0.2,
    top_p: 1,
    presence_penalty: 0,
    frequency_penalty: 0,
    max_tokens: 900,
    deep_research_temperature: 0.1,
    deep_research_top_p: 1,
    deep_research_presence_penalty: 0,
    deep_research_frequency_penalty: 0,
    deep_research_max_tokens: 1600,
};

export { DEFAULT_LLM_SETTINGS };
