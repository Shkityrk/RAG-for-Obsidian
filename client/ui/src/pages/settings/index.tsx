import BasicLayout from "../../layouts/basic-layout"
import {
    Stack,
    Select,
    useComputedColorScheme,
    useMantineColorScheme,
    MantineColorScheme,
    Title,
    Text,
    TextInput,
    PasswordInput,
    NumberInput,
    Button,
    Group,
    Divider,
    Loader,
} from '@mantine/core';
import { useEffect, useState } from "react";
import { useCheckLLM, useLLMSettings, useUpdateLLMSettings } from "../../hooks/settings";
import { LLMSettingsRequest } from "../../types/settings";
import {
    DEFAULT_LLM_SETTINGS,
    DEEP_RESEARCH_MODEL_SUGGESTIONS,
    OPENROUTER_MODEL_SUGGESTIONS,
} from "./settings_config";

export const SettingsPage = () => {
    const { setColorScheme } = useMantineColorScheme();
    const computedColorScheme = useComputedColorScheme('light', { getInitialValueInEffect: true });
    const [form, setForm] = useState<LLMSettingsRequest>(DEFAULT_LLM_SETTINGS);
    const { data, isLoading } = useLLMSettings();
    const { mutateAsync: updateSettings, isPending: isSaving } = useUpdateLLMSettings();
    const { mutateAsync: checkSettings, isPending: isChecking } = useCheckLLM();

    useEffect(() => {
        if (data) {
            setForm(data);
        }
    }, [data]);

    const updateField = <K extends keyof LLMSettingsRequest>(key: K, value: LLMSettingsRequest[K]) => {
        setForm((prev) => ({ ...prev, [key]: value }));
    };

    const numberValue = (value: string | number, fallback: number): number => {
        if (typeof value === "number" && Number.isFinite(value)) {
            return value;
        }
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    };

    return (
        <BasicLayout>
            <Stack gap="xl" p={{ base: "md", sm: "xl" }} maw={600} mx="auto" pt={{ base: 16, sm: 32 }}>
                <Title order={2} fw={600} mb="md">Settings</Title>
                
                <Stack gap="md">
                    <div>
                        <Text size="sm" fw={500} mb={8}>Theme</Text>
                        <Select
                            variant="default"
                            size="md"
                            w="100%"
                            data={[{label: "Dark", value: "dark"}, {label: "Light", value: "light"}]}
                            value={computedColorScheme} 
                            onChange={value => value && setColorScheme(value as MantineColorScheme)}
                        />
                    </div>
                </Stack>

                <Divider />

                <Stack gap="md">
                    <Title order={4}>OpenRouter</Title>
                    {isLoading ? (
                        <Loader size="sm" />
                    ) : (
                        <>
                            <PasswordInput
                                label="OPENROUTER_API_KEY"
                                placeholder="sk-or-v1-..."
                                value={form.openrouter_api_key}
                                onChange={(event) => updateField("openrouter_api_key", event.currentTarget.value)}
                            />
                            <TextInput
                                label="OPENROUTER_LLM_MODEL"
                                placeholder="google/gemini-3-flash-preview"
                                value={form.openrouter_llm_model}
                                onChange={(event) => updateField("openrouter_llm_model", event.currentTarget.value)}
                                description={`Examples: ${OPENROUTER_MODEL_SUGGESTIONS.join(", ")}`}
                            />
                            <TextInput
                                label="OPENROUTER_DEEP_RESEARCH_MODEL"
                                placeholder="perplexity/sonar-deep-research"
                                value={form.openrouter_deep_research_model}
                                onChange={(event) => updateField("openrouter_deep_research_model", event.currentTarget.value)}
                                description={`Examples: ${DEEP_RESEARCH_MODEL_SUGGESTIONS.join(", ")}`}
                            />

                            <Divider label="Chat Model Params" />
                            <NumberInput
                                label="temperature"
                                value={form.temperature}
                                onChange={(value) => updateField("temperature", numberValue(value, form.temperature))}
                                min={0}
                                max={2}
                                step={0.1}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="top_p"
                                value={form.top_p}
                                onChange={(value) => updateField("top_p", numberValue(value, form.top_p))}
                                min={0}
                                max={1}
                                step={0.05}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="presence_penalty"
                                value={form.presence_penalty}
                                onChange={(value) => updateField("presence_penalty", numberValue(value, form.presence_penalty))}
                                min={-2}
                                max={2}
                                step={0.1}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="frequency_penalty"
                                value={form.frequency_penalty}
                                onChange={(value) => updateField("frequency_penalty", numberValue(value, form.frequency_penalty))}
                                min={-2}
                                max={2}
                                step={0.1}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="max_tokens"
                                value={form.max_tokens}
                                onChange={(value) => updateField("max_tokens", numberValue(value, form.max_tokens))}
                                min={64}
                                max={32000}
                                step={64}
                            />

                            <Divider label="Deep Research Params" />
                            <NumberInput
                                label="deep_research_temperature"
                                value={form.deep_research_temperature}
                                onChange={(value) => updateField("deep_research_temperature", numberValue(value, form.deep_research_temperature))}
                                min={0}
                                max={2}
                                step={0.1}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="deep_research_top_p"
                                value={form.deep_research_top_p}
                                onChange={(value) => updateField("deep_research_top_p", numberValue(value, form.deep_research_top_p))}
                                min={0}
                                max={1}
                                step={0.05}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="deep_research_presence_penalty"
                                value={form.deep_research_presence_penalty}
                                onChange={(value) => updateField("deep_research_presence_penalty", numberValue(value, form.deep_research_presence_penalty))}
                                min={-2}
                                max={2}
                                step={0.1}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="deep_research_frequency_penalty"
                                value={form.deep_research_frequency_penalty}
                                onChange={(value) => updateField("deep_research_frequency_penalty", numberValue(value, form.deep_research_frequency_penalty))}
                                min={-2}
                                max={2}
                                step={0.1}
                                decimalScale={2}
                            />
                            <NumberInput
                                label="deep_research_max_tokens"
                                value={form.deep_research_max_tokens}
                                onChange={(value) => updateField("deep_research_max_tokens", numberValue(value, form.deep_research_max_tokens))}
                                min={64}
                                max={64000}
                                step={64}
                            />

                            <Group justify="space-between" mt="sm">
                                <Button
                                    variant="light"
                                    loading={isChecking}
                                    onClick={() => checkSettings(form)}
                                >
                                    Check
                                </Button>
                                <Button
                                    loading={isSaving}
                                    onClick={() => updateSettings(form)}
                                >
                                    Save
                                </Button>
                            </Group>
                        </>
                    )}
                </Stack>
            </Stack>
        </BasicLayout>
    );
}
