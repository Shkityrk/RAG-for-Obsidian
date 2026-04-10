import BasicLayout from "../../layouts/basic-layout"
import {Stack, Select, useComputedColorScheme, useMantineColorScheme, MantineColorScheme, Title, Text } from '@mantine/core';

export const SettingsPage = () => {
    const { setColorScheme } = useMantineColorScheme();
    const computedColorScheme = useComputedColorScheme('light', { getInitialValueInEffect: true });

    return (
        <BasicLayout>
            <Stack gap="xl" p="xl" maw={600} mx="auto" pt={32}>
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
            </Stack>
        </BasicLayout>
    );
}