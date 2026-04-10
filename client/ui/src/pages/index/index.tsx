import {Title, Stack, Progress, Group, Button, Text, Paper, Box, LoadingOverlay } from '@mantine/core';
import { useState, useEffect } from 'react';
import { ScatterChart } from '@mantine/charts';
import { useClusters, useIndexInfo, useDeleteIndex, useUpdateIndex, useIndexProgress } from "../../hooks/update-index";
import { useVaults } from "../../hooks/vaults";
import { ClusterSchema } from '../../types/update-index';
import { getRandomColorAndNumber } from "../../utils/random-color"
import { formatDatetime } from "../../utils/format-datetime"
import BasicLayout from "../../layouts/basic-layout"



const toScatterChartSeries = (clusters: Array<ClusterSchema>) => {
    return clusters.map(cluster => {
        return {
            color: getRandomColorAndNumber(),
            name: cluster.name,
            data: [
                {x: cluster.x, y: cluster.y}
            ]
        }
    })
}


const ChartTooltip = (props: {payload: {name: string, x: number, y: number}}) => {
    if (!props.payload) return null;
    if (!props.payload["name"]) return null;
    return (
      <Paper px="md" py="sm" withBorder shadow="md" radius="md">
          <Text fz="xs">
            {props.payload.name}
          </Text>
      </Paper>
    );
  }
  


export const IndexPage = () => {
    const [shouldFetch, setShouldFetch] = useState(false);
    const [selectedVaultId, setSelectedVaultId] = useState<number | null>(null);
    
    const { data: vaultsData } = useVaults();

    // Автоматически используем первый (и единственный) vault
    useEffect(() => {
        if (vaultsData?.vaults && vaultsData.vaults.length > 0 && !selectedVaultId) {
            setSelectedVaultId(vaultsData.vaults[0].id);
        }
    }, [vaultsData, selectedVaultId]);

    const {data: clusterData, isSuccess: isClusterSuccess,  isLoading: isClusterLoading} = useClusters(selectedVaultId);
    const {data: indexInfo, isSuccess: isIndexInfoSuccess, isLoading: isIndexInfoLoading, refetch: refetchIndexInfo} = useIndexInfo(selectedVaultId);
    const {mutateAsync: deleteIndex, isPending: isDeletePending} = useDeleteIndex();
    const {mutateAsync: startUpdateIndex, isPending: isUpdatePending} = useUpdateIndex();
    const {data: indexProgress, isSuccess: isProgressSuccess} = useIndexProgress(selectedVaultId, shouldFetch);

    useEffect(() => {
        if (isProgressSuccess && indexProgress && !indexProgress.in_progress) {
            setShouldFetch(false);
        }
      }, [indexProgress, isProgressSuccess]);

    
    const updateIndex = () => {
        if (!selectedVaultId) {
            alert('Vault is not available. Please wait for vault to load.');
            return;
        }
        startUpdateIndex(selectedVaultId);
        setShouldFetch(true);
    }
    
    const handleDeleteIndex = () => {
        if (!selectedVaultId) {
            alert('Vault is not available. Please wait for vault to load.');
            return;
        }
        deleteIndex(selectedVaultId);
    }

    return (
        <BasicLayout>
            <Stack gap="xl" p="xl" maw={1200} mx="auto" pt={32}>
                {selectedVaultId ? (
                    <>
                        <Box pos="relative" style={{borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--border-color)'}}>
                            <LoadingOverlay visible={isClusterLoading} zIndex={1000} loaderProps={{ color: 'blue', type: 'bars' }} overlayProps={{ radius: "sm", blur: 1 }} />
                            <ScatterChart
                                h={400}
                                data={isClusterSuccess? toScatterChartSeries(clusterData.clusters): []}
                                dataKey={{ x: 'x', y: 'y' }}
                                xAxisLabel=""
                                yAxisLabel=""
                                withYAxis={false}
                                withXAxis={false}
                                gridAxis="xy"
                                tooltipProps={{offset:0, content: ({payload}) => payload && payload.length && <ChartTooltip payload={payload[0].payload} />}}
                            />
                        </Box>
                        <Group gap="md">
                            <Button 
                                onClick={() => refetchIndexInfo()} 
                                disabled={isIndexInfoLoading} 
                                loading={isIndexInfoLoading} 
                                loaderProps={{type: "dots"}}
                                variant="light"
                            >
                                Refresh info
                            </Button>
                            <Button 
                                onClick={updateIndex} 
                                disabled={isDeletePending || isUpdatePending} 
                                loading={isUpdatePending} 
                                loaderProps={{type: "dots"}}
                                variant="filled"
                            >
                                Update Index
                            </Button>
                            <Button 
                                onClick={handleDeleteIndex} 
                                disabled={isDeletePending || isUpdatePending} 
                                loading={isDeletePending} 
                                loaderProps={{type: "dots"}}
                                variant="light"
                                color="red"
                            >
                                Remove Index
                            </Button>
                        </Group>
                        <Stack gap="md">
                            <Title order={3} fw={600} mb="sm">
                                General information
                            </Title>
                            <Stack gap="xs">
                                <Text size="sm">
                                    <Text span fw={500}>Last updated:</Text> {isIndexInfoLoading? "loading...": isIndexInfoSuccess && indexInfo.last_update_time? formatDatetime(indexInfo.last_update_time): "not found"}
                                </Text>
                                <Text size="sm">
                                    <Text span fw={500}>Total documents:</Text> {isIndexInfoLoading? "loading...": isIndexInfoSuccess? indexInfo.n_all_documents: "not found"}
                                </Text>
                                <Text size="sm">
                                    <Text span fw={500}>Documents to update:</Text> {isIndexInfoLoading? "loading...": isIndexInfoSuccess? indexInfo.n_documents_to_update: "not found"}
                                </Text>
                            </Stack>
                        </Stack>
                        {
                            isProgressSuccess && indexProgress.in_progress && (
                                <Stack gap="md">
                                    <Title order={3} fw={600}>
                                        Update progress
                                    </Title>
                                    {
                                        indexProgress.stages.map(
                                            (stage, index) => (
                                                <Stack key={index} gap="xs">
                                                    <Text size="sm" fw={500}>
                                                        {stage.name}
                                                    </Text>
                                                    <Progress value={stage.value} animated size="lg" radius="md" />
                                                </Stack>
                                            )
                                        )
                                    }
                                </Stack>
                            )
                        }
                    </>
                ) : (
                    <Text c="dimmed" ta="center" py="xl">
                        Vault is loading...
                    </Text>
                )}
            </Stack>
        </BasicLayout>
    );
}
