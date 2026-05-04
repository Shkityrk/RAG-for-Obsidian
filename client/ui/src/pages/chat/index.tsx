import BasicLayout from "../../layouts/basic-layout"
import MessageHistory from "../../components/message-history"
import DocumentViewer from "../../components/document-viewer"
import { ScrollArea, Textarea, ActionIcon, Flex, Button, List, Text, Accordion, Stack, Group, Paper, Loader, Drawer, Modal, Badge, ThemeIcon, Tooltip } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconArrowRight, IconInfoHexagonFilled, IconBookmarksFilled, IconSettingsFilled, IconPlus, IconSearch, IconMenu2, IconMessageCircle, IconDatabase, IconSparkles } from '@tabler/icons-react';
import { useEffect, useRef, useState } from "react";
import { useChatMessages, useSendChatMessage, useCleanChatMessage, useSendDeepResearchMessage } from "../../hooks/messages";
import { useLLMTokens } from "../../hooks/llm-tokens";
import { useChats, useCreateChat } from "../../hooks/chats";
import { useVaults } from "../../hooks/vaults";
import { MessageSchema, FragmentInfo } from "../../types/messages";
import { useSearchParams } from "react-router-dom";
import "./index.css";

export const ChatPage = () => {
    const viewport = useRef<HTMLDivElement | null>(null);
    const [searchParams, setSearchParams] = useSearchParams();
    
    const chatIdParam = searchParams.get('chat_id');
    const chatId = chatIdParam ? parseInt(chatIdParam) : null;
    
    const [messages, setMessages] = useState<Array<MessageSchema>>([]);
    const [userCurrentMessage, setUserCurrentMessage] = useState("");
    const [relatedDocuments, setRelatedDocuments] = useState<Array<string>>([]);
    const [selectedVaultId, setSelectedVaultId] = useState<number | null>(null);
    const [messageFragments, setMessageFragments] = useState<Map<string | number, FragmentInfo[]>>(new Map());
    const [selectedFragment, setSelectedFragment] = useState<FragmentInfo | null>(null);
    const [showDocumentViewer, setShowDocumentViewer] = useState(false);
    const [selectedMessageId, setSelectedMessageId] = useState<number | string | null>(null);
    const [chatsDrawerOpened, { toggle: toggleChatsDrawer, close: closeChatsDrawer }] = useDisclosure(false);
    const [infoDrawerOpened, { toggle: toggleInfoDrawer, close: closeInfoDrawer }] = useDisclosure(false);
    
    const { data: chatsData, isLoading: chatsLoading } = useChats();
    const { data: vaultsData } = useVaults();
    const { data, isSuccess } = useChatMessages(chatId);
    const { data: llmTokens, isSuccess: isLLMTokensSuccess } = useLLMTokens();
    const { mutateAsync: sendMessage, isPending: isSendMessagePending } = useSendChatMessage();
    const { mutateAsync: sendDeepResearch, isPending: isDeepResearchPending } = useSendDeepResearchMessage();
    const { mutateAsync: cleanMessages, isPending: isCleanMessagesPending } = useCleanChatMessage();
    const { mutateAsync: createChat, isPending: isCreateChatPending } = useCreateChat();

    // Инициализация vault_id из первого доступного волта (единственный vault)
    useEffect(() => {
        if (vaultsData?.vaults && vaultsData.vaults.length > 0 && !selectedVaultId) {
            // Используем первый (и единственный) vault
            setSelectedVaultId(vaultsData.vaults[0].id);
        }
    }, [vaultsData, selectedVaultId]);

    useEffect(() => {
        if (data) {
            setMessages(data.messages);
            // Загружаем fragments из БД для каждого сообщения
            const fragmentsMap = new Map<string | number, FragmentInfo[]>();
            data.messages.forEach(message => {
                if (message.fragments && message.fragments.length > 0) {
                    fragmentsMap.set(message.id, message.fragments);
                    // Также сохраняем как string и number для совместимости
                    fragmentsMap.set(String(message.id), message.fragments);
                    fragmentsMap.set(Number(message.id), message.fragments);
                }
            });
            if (fragmentsMap.size > 0) {
                setMessageFragments(fragmentsMap);
            }
        }
    }, [isSuccess, data]);

    useEffect(() => {
        if (viewport.current) {
            viewport.current.scrollTo({ top: viewport.current.scrollHeight, behavior: 'smooth' });
        }
    }, [messages]);

    const handleChatChange = (newChatId: number | null) => {
        if (newChatId) {
            setSearchParams({ chat_id: newChatId.toString() });
        } else {
            setSearchParams({});
        }
    };

    const handleCreateChat = async () => {
        if (!selectedVaultId) {
            alert('Vault недоступен. Дождитесь загрузки.');
            return;
        }
        try {
            const newChat = await createChat({ vault_id: selectedVaultId, title: 'Новый чат' });
            handleChatChange(newChat.id);
        } catch (error: unknown) {
            const errorMessage = (
                typeof error === 'object' &&
                error !== null &&
                ((error as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
                    (error as { message?: string }).message)
            ) || 'Не удалось создать чат';
            alert(`Ошибка создания чата: ${errorMessage}`);
        }
    };

    const sendMessageWrapper = () => {
        if (!userCurrentMessage.trim()) return;
        if (!chatId) {
            alert('Сначала выберите или создайте чат');
            return;
        }
        if (!selectedVaultId) {
            alert('Vault недоступен. Дождитесь загрузки.');
            return;
        }

        const messageContent = userCurrentMessage;
        setMessages(messages => [...messages, {
            role: "user",
            content: messageContent,
            datetime: new Date().toISOString(),
            id: new Date().getTime().toString()
        }]);
        setUserCurrentMessage("");

        sendMessage({
            content: messageContent,
            chat_id: chatId,
            vault_id: selectedVaultId
        }).then((data) => {
            // Используем ID сообщения из БД вместо временного
            const assistantMessageId = data.message_id;
            
            // Сохраняем fragments с ID из БД (и как string, и как number для совместимости)
            if (data.fragments && data.fragments.length > 0) {
                setMessageFragments(prev => {
                    const newMap = new Map(prev);
                    // Сохраняем и как number, и как string для совместимости
                    newMap.set(assistantMessageId, data.fragments);
                    newMap.set(String(assistantMessageId), data.fragments);
                    return newMap;
                });
            }
            
            // Добавляем сообщение с ID из БД
            setMessages(messages => [...messages, {
                role: "assistant",
                content: data.answer,
                datetime: new Date().toISOString(),
                id: assistantMessageId
            }]);
            setRelatedDocuments(() => data.related_documents);
        }, () => {
            // Удаляем сообщение пользователя при ошибке
            setMessages(messages => messages.slice(0, -1));
        });
    };

    const sendDeepResearchWrapper = () => {
        if (!userCurrentMessage.trim()) return;
        if (!chatId) {
            alert('Сначала выберите или создайте чат');
            return;
        }
        if (!selectedVaultId) {
            alert('Vault недоступен. Дождитесь загрузки.');
            return;
        }

        const messageContent = userCurrentMessage;
        setMessages(messages => [...messages, {
            role: "user",
            content: messageContent,
            datetime: new Date().toISOString(),
            id: new Date().getTime().toString()
        }]);
        setUserCurrentMessage("");

        sendDeepResearch({
            content: messageContent,
            chat_id: chatId,
            vault_id: selectedVaultId
        }).then((data) => {
            const assistantMessageId = data.message_id;
            
            if (data.fragments && data.fragments.length > 0) {
                setMessageFragments(prev => {
                    const newMap = new Map(prev);
                    newMap.set(assistantMessageId, data.fragments);
                    newMap.set(String(assistantMessageId), data.fragments);
                    return newMap;
                });
            }
            
            setMessages(messages => [...messages, {
                role: "assistant",
                content: data.answer,
                datetime: new Date().toISOString(),
                id: assistantMessageId
            }]);
            setRelatedDocuments(() => data.related_documents);
        }, () => {
            setMessages(messages => messages.slice(0, -1));
        });
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessageWrapper();
        }
    };

    const cleanMessagesWrapper = () => {
        if (!chatId) return;
        setRelatedDocuments([]);
        setMessageFragments(new Map());
        setSelectedFragment(null);
        setShowDocumentViewer(false);
        cleanMessages(chatId);
    };

    const handleFragmentClick = (fragment: FragmentInfo, messageId: number | string) => {
        setSelectedFragment(fragment);
        setSelectedMessageId(messageId);
        setShowDocumentViewer(true);
        closeChatsDrawer();
        closeInfoDrawer();
    };

    const availableChats = chatsData?.chats || [];
    const activeChatTitle = chatId ? availableChats.find(c => c.id === chatId)?.title || 'Чат' : 'RAG Chat';
    const totalTokens = isLLMTokensSuccess ? llmTokens.input_tokens + llmTokens.output_tokens : null;
    const canSendMessage = Boolean(selectedVaultId && userCurrentMessage.trim() && chatId);

    return (
        <BasicLayout>
            <div className="chat-container">
                <Flex direction={"row"} h="100%" gap={0}>
                    {/* Sidebar с чатами - Desktop */}
                    <div className="chat-sidebar">
                        <Stack gap="sm">
                            <Group justify="space-between" align="center">
                                <div>
                                    <Text size="xs" c="dimmed" fw={700}>Рабочая область</Text>
                                    <Text size="sm" fw={800}>Чаты</Text>
                                </div>
                                <Button
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconPlus size={14} />}
                                    onClick={handleCreateChat}
                                    loading={isCreateChatPending}
                                    disabled={!selectedVaultId}
                                >
                                    Новый
                                </Button>
                            </Group>

                            <ScrollArea scrollbars="y" h={400}>
                                <Stack gap="xs">
                                    {chatsLoading ? (
                                        <Loader size="sm" />
                                    ) : availableChats.length === 0 ? (
                                        <Text size="sm" c="dimmed">Чатов пока нет</Text>
                                    ) : (
                                        availableChats.map((chat) => (
                                            <Paper
                                                key={chat.id}
                                                p="xs"
                                                className={`chat-list-item ${chat.id === chatId ? 'active' : ''}`}
                                                onClick={() => handleChatChange(chat.id)}
                                            >
                                                <Text size="sm" truncate>{chat.title}</Text>
                                                <Text size="xs" c="dimmed">
                                                    {new Date(chat.updated_at).toLocaleDateString()}
                                                </Text>
                                            </Paper>
                                        ))
                                    )}
                                </Stack>
                            </ScrollArea>
                        </Stack>
                    </div>

                    {/* Mobile Drawer для чатов */}
                    <Drawer
                        opened={chatsDrawerOpened}
                        onClose={closeChatsDrawer}
                        title="Чаты"
                        position="left"
                        padding="md"
                        size="xs"
                        className="mobile-chats-drawer"
                    >
                        <Stack gap="sm">
                            <Group justify="space-between">
                                <Text size="sm" fw={600}>Чаты</Text>
                                <Button
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconPlus size={14} />}
                                    onClick={handleCreateChat}
                                    loading={isCreateChatPending}
                                    disabled={!selectedVaultId}
                                >
                                    Новый
                                </Button>
                            </Group>

                            <ScrollArea scrollbars="y" h={400}>
                                <Stack gap="xs">
                                    {chatsLoading ? (
                                        <Loader size="sm" />
                                    ) : availableChats.length === 0 ? (
                                        <Text size="sm" c="dimmed">Чатов пока нет</Text>
                                    ) : (
                                        availableChats.map((chat) => (
                                            <Paper
                                                key={chat.id}
                                                p="xs"
                                                style={{
                                                    cursor: 'pointer',
                                                    backgroundColor: chat.id === chatId ? 'var(--bg-primary)' : 'transparent',
                                                    border: chat.id === chatId ? '1px solid var(--border-color)' : 'none',
                                                }}
                                                onClick={() => {
                                                    handleChatChange(chat.id);
                                                    closeChatsDrawer();
                                                }}
                                            >
                                                <Text size="sm" truncate>{chat.title}</Text>
                                                <Text size="xs" c="dimmed">
                                                    {new Date(chat.updated_at).toLocaleDateString()}
                                                </Text>
                                            </Paper>
                                        ))
                                    )}
                                </Stack>
                            </ScrollArea>
                        </Stack>
                    </Drawer>

                    {/* Основная область чата */}
                    <Flex direction={"column"} h="100%" style={{ flex: 1 }} className="chat-main-area">
                        {/* Mobile header с кнопками */}
                        <div className="chat-mobile-header">
                            <ActionIcon
                                variant="light"
                                onClick={toggleChatsDrawer}
                                size="lg"
                                aria-label="Открыть чаты"
                            >
                                <IconMenu2 size={20} />
                            </ActionIcon>
                            <Text size="sm" fw={500}>
                                {activeChatTitle}
                            </Text>
                            <ActionIcon
                                variant="light"
                                onClick={toggleInfoDrawer}
                                size="lg"
                                aria-label="Открыть информацию"
                            >
                                <IconInfoHexagonFilled size={20} />
                            </ActionIcon>
                        </div>

                        {!chatId ? (
                            <div className="chat-empty-state">
                                <ThemeIcon size={52} radius="md" variant="light" color="blue">
                                    <IconMessageCircle size={26} />
                                </ThemeIcon>
                                <div>
                                    <Text size="lg" fw={800}>Чат не выбран</Text>
                                    <Text size="sm" c="dimmed">Создайте диалог и задавайте вопросы по вашему synced vault.</Text>
                                </div>
                                <Button
                                    onClick={handleCreateChat}
                                    loading={isCreateChatPending}
                                    disabled={!selectedVaultId}
                                    leftSection={<IconPlus size={16} />}
                                >
                                    Создать чат
                                </Button>
                            </div>
                        ) : (
                            <>
                                <Flex direction="row" className="chat-messages-wrapper" style={{ flex: 1, overflow: 'hidden' }}>
                                    <ScrollArea
                                        viewportRef={viewport}
                                        offsetScrollbars
                                        className="chat-messages-area"
                                        style={{ flex: showDocumentViewer ? '0 0 60%' : 1 }}
                                    >
                                        <div className="chat-thread-header">
                                            <div>
                                                <Text size="xs" c="dimmed" fw={700}>Текущий диалог</Text>
                                                <Text fw={800}>{activeChatTitle}</Text>
                                            </div>
                                            <Group gap="xs">
                                                <Badge variant="light" color={selectedVaultId ? "blue" : "gray"} leftSection={<IconDatabase size={12} />}>
                                                    {selectedVaultId ? "Vault готов" : "Vault загружается"}
                                                </Badge>
                                                {totalTokens !== null && (
                                                    <Badge variant="light" color="teal">
                                                        {totalTokens} токенов
                                                    </Badge>
                                                )}
                                            </Group>
                                        </div>
                                        <MessageHistory 
                                            messages={messages} 
                                            isAssistantThinking={isSendMessagePending || isDeepResearchPending}
                                            messageFragments={messageFragments}
                                            vaultId={selectedVaultId || undefined}
                                            onFragmentClick={handleFragmentClick}
                                        />
                                    </ScrollArea>
                                    {/* DocumentViewer - модальный на мобильных */}
                                    {showDocumentViewer && selectedFragment && selectedVaultId && selectedMessageId && (
                                        <>
                                            {/* Desktop */}
                                            <div className="chat-document-viewer-desktop">
                                                <DocumentViewer
                                                    vaultId={selectedVaultId}
                                                    filename={selectedFragment.filename}
                                                    fragments={messageFragments.get(selectedMessageId) || 
                                                              messageFragments.get(String(selectedMessageId)) ||
                                                              messageFragments.get(Number(selectedMessageId)) ||
                                                              []}
                                                    onClose={() => {
                                                        setShowDocumentViewer(false);
                                                        setSelectedFragment(null);
                                                        setSelectedMessageId(null);
                                                    }}
                                                />
                                            </div>
                                            {/* Mobile Modal */}
                                            <Modal
                                                opened={showDocumentViewer}
                                                onClose={() => {
                                                    setShowDocumentViewer(false);
                                                    setSelectedFragment(null);
                                                    setSelectedMessageId(null);
                                                }}
                                                title={selectedFragment.filename}
                                                size="xl"
                                                fullScreen
                                                className="chat-document-viewer-mobile"
                                            >
                                                <DocumentViewer
                                                    vaultId={selectedVaultId}
                                                    filename={selectedFragment.filename}
                                                    fragments={messageFragments.get(selectedMessageId) || 
                                                              messageFragments.get(String(selectedMessageId)) ||
                                                              messageFragments.get(Number(selectedMessageId)) ||
                                                              []}
                                                    onClose={() => {
                                                        setShowDocumentViewer(false);
                                                        setSelectedFragment(null);
                                                        setSelectedMessageId(null);
                                                    }}
                                                />
                                            </Modal>
                                        </>
                                    )}
                                </Flex>
                                <div className="chat-input-container">
                                    <Flex gap="xs" align="flex-end">
                                        <Textarea
                                            autoFocus={true}
                                            value={userCurrentMessage}
                                            onChange={e => setUserCurrentMessage(e.target.value)}
                                            radius="md"
                                            size="lg"
                                            autosize={true}
                                            minRows={1}
                                            maxRows={6}
                                            onKeyDown={handleKeyDown}
                                            placeholder="Спросите что-нибудь о вашем vault..."
                                            disabled={!selectedVaultId}
                                            style={{ flex: 1 }}
                                            styles={{
                                                input: {
                                                    fontSize: '15px',
                                                    paddingRight: '16px',
                                                    paddingLeft: '16px',
                                                    paddingTop: '12px',
                                                    paddingBottom: '12px',
                                                    border: '1px solid var(--border-color)',
                                                    backgroundColor: 'var(--bg-secondary)',
                                                }
                                            }}
                                        />
                                        <Tooltip label="Deep Research">
                                            <ActionIcon
                                                loaderProps={{ type: "oval" }}
                                                loading={isDeepResearchPending}
                                                size={42}
                                                radius="md"
                                                color="teal"
                                                variant="light"
                                                onClick={sendDeepResearchWrapper}
                                                disabled={!canSendMessage}
                                                title="Deep Research"
                                            >
                                                <IconSearch style={{ width: 20, height: 20 }} stroke={2} />
                                            </ActionIcon>
                                        </Tooltip>
                                        <Tooltip label="Отправить">
                                            <ActionIcon
                                                loaderProps={{ type: "oval" }}
                                                loading={isSendMessagePending}
                                                size={42}
                                                radius="md"
                                                color="blue"
                                                variant="filled"
                                                onClick={sendMessageWrapper}
                                                disabled={!canSendMessage}
                                                title="Отправить"
                                            >
                                                <IconArrowRight style={{ width: 20, height: 20 }} stroke={2} />
                                            </ActionIcon>
                                        </Tooltip>
                                    </Flex>
                                </div>
                            </>
                        )}
                    </Flex>

                    {/* Правая панель с информацией - Desktop */}
                    <div className="chat-info-sidebar">
                        <div className="chat-info-summary">
                            <ThemeIcon size={38} radius="md" variant="light" color="blue">
                                <IconSparkles size={20} />
                            </ThemeIcon>
                            <div>
                                <Text size="sm" fw={800}>Статус RAG</Text>
                                <Text size="xs" c="dimmed">Контекст, источники и управление</Text>
                            </div>
                        </div>
                        <Accordion multiple={true} defaultValue={["general"]} variant="default">
                            <Accordion.Item value={"general"}>
                                <Accordion.Control icon={<IconInfoHexagonFilled size={18} />}>
                                    <Text size="sm" fw={500}>Общее</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    <Stack gap="xs">
                                        <div>
                                            <Text size="xs" c="dimmed">Входные токены</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.input_tokens : "—"}</Text>
                                        </div>
                                        <div>
                                            <Text size="xs" c="dimmed">Выходные токены</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.output_tokens : "—"}</Text>
                                        </div>
                                    </Stack>
                                </Accordion.Panel>
                            </Accordion.Item>
                            <Accordion.Item value={"related"}>
                                <Accordion.Control icon={<IconBookmarksFilled size={18} />}>
                                    <Text size="sm" fw={500}>Связанные документы</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    {relatedDocuments.length === 0 ? (
                                        <Text size="sm" c="dimmed">Документов нет</Text>
                                    ) : (
                                        <ScrollArea scrollbars="y" h={200}>
                                            <List
                                                spacing="xs"
                                                size="sm"
                                                center={false}
                                            >
                                                {relatedDocuments.map((doc, index) => (
                                                    <List.Item key={index}>
                                                        <Text size="sm" fw={400}>
                                                            {doc}
                                                        </Text>
                                                    </List.Item>
                                                ))}
                                            </List>
                                        </ScrollArea>
                                    )}
                                </Accordion.Panel>
                            </Accordion.Item>
                            <Accordion.Item value={"management"}>
                                <Accordion.Control icon={<IconSettingsFilled size={18} />}>
                                    <Text size="sm" fw={500}>Управление</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    <Button
                                        variant="light"
                                        size="sm"
                                        loaderProps={{ type: "dots" }}
                                        loading={isCleanMessagesPending}
                                        onClick={cleanMessagesWrapper}
                                        disabled={!chatId}
                                        fullWidth
                                    >
                                        Очистить историю
                                    </Button>
                                </Accordion.Panel>
                            </Accordion.Item>
                        </Accordion>
                    </div>

                    {/* Mobile Drawer для информации */}
                    <Drawer
                        opened={infoDrawerOpened}
                        onClose={closeInfoDrawer}
                        title="Информация"
                        position="right"
                        padding="md"
                        size="xs"
                        className="mobile-info-drawer"
                    >
                        <Accordion multiple={true} defaultValue={["general"]} variant="default">
                            <Accordion.Item value={"general"}>
                                <Accordion.Control icon={<IconInfoHexagonFilled size={18} />}>
                                    <Text size="sm" fw={500}>Общее</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    <Stack gap="xs">
                                        <div>
                                            <Text size="xs" c="dimmed">Входные токены</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.input_tokens : "—"}</Text>
                                        </div>
                                        <div>
                                            <Text size="xs" c="dimmed">Выходные токены</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.output_tokens : "—"}</Text>
                                        </div>
                                    </Stack>
                                </Accordion.Panel>
                            </Accordion.Item>
                            <Accordion.Item value={"related"}>
                                <Accordion.Control icon={<IconBookmarksFilled size={18} />}>
                                    <Text size="sm" fw={500}>Связанные документы</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    {relatedDocuments.length === 0 ? (
                                        <Text size="sm" c="dimmed">Документов нет</Text>
                                    ) : (
                                        <ScrollArea scrollbars="y" h={200}>
                                            <List
                                                spacing="xs"
                                                size="sm"
                                                center={false}
                                            >
                                                {relatedDocuments.map((doc, index) => (
                                                    <List.Item key={index}>
                                                        <Text size="sm" fw={400}>
                                                            {doc}
                                                        </Text>
                                                    </List.Item>
                                                ))}
                                            </List>
                                        </ScrollArea>
                                    )}
                                </Accordion.Panel>
                            </Accordion.Item>
                            <Accordion.Item value={"management"}>
                                <Accordion.Control icon={<IconSettingsFilled size={18} />}>
                                    <Text size="sm" fw={500}>Управление</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    <Button
                                        variant="light"
                                        size="sm"
                                        loaderProps={{ type: "dots" }}
                                        loading={isCleanMessagesPending}
                                        onClick={() => {
                                            cleanMessagesWrapper();
                                            closeInfoDrawer();
                                        }}
                                        disabled={!chatId}
                                        fullWidth
                                    >
                                        Очистить историю
                                    </Button>
                                </Accordion.Panel>
                            </Accordion.Item>
                        </Accordion>
                    </Drawer>
                </Flex>
            </div>
        </BasicLayout>
    );
}
