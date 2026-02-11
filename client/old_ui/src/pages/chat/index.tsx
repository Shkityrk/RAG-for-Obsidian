import BasicLayout from "../../layouts/basic-layout"
import MessageHistory from "../../components/message-history"
import DocumentViewer from "../../components/document-viewer"
import { ScrollArea, Textarea, ActionIcon, Flex, Button, List, Text, Accordion, Stack, Select, Group, Paper, Loader, Drawer, Modal } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconArrowRight, IconInfoHexagonFilled, IconBookmarksFilled, IconSettingsFilled, IconPlus, IconSearch, IconMenu2 } from '@tabler/icons-react';
import { useEffect, useRef, useState } from "react";
import { useChatMessages, useSendChatMessage, useCleanChatMessage, useSendCombinedSearchMessage } from "../../hooks/messages";
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
    const { data: vaultsData, isLoading: vaultsLoading } = useVaults();
    const { data, isSuccess } = useChatMessages(chatId);
    const { data: llmTokens, isSuccess: isLLMTokensSuccess } = useLLMTokens();
    const { mutateAsync: sendMessage, isPending: isSendMessagePending } = useSendChatMessage();
    const { mutateAsync: sendCombinedSearch, isPending: isCombinedSearchPending } = useSendCombinedSearchMessage();
    const { mutateAsync: cleanMessages, isPending: isCleanMessagesPending } = useCleanChatMessage();
    const { mutateAsync: createChat, isPending: isCreateChatPending } = useCreateChat();

    // Инициализация vault_id из первого доступного волта или из выбранного чата
    useEffect(() => {
        if (vaultsData?.vaults && vaultsData.vaults.length > 0 && !selectedVaultId) {
            // Если есть чат, используем его vault_id, иначе берем первый волт
            if (chatId && chatsData?.chats) {
                const chat = chatsData.chats.find(c => c.id === chatId);
                if (chat?.vault_id) {
                    setSelectedVaultId(chat.vault_id);
                    return;
                }
            }
            setSelectedVaultId(vaultsData.vaults[0].id);
        }
    }, [vaultsData, chatsData, chatId, selectedVaultId]);

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
                console.log('Loaded fragments from DB:', Array.from(fragmentsMap.entries()).map(([k, v]) => [`${k}(${typeof k})`, v.length]));
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
            alert('Please select a vault first');
            return;
        }
        try {
            const newChat = await createChat({ vault_id: selectedVaultId, title: 'New Chat' });
            handleChatChange(newChat.id);
        } catch (error) {
            console.error(error);
        }
    };

    const sendMessageWrapper = () => {
        if (!userCurrentMessage.trim()) return;
        if (!chatId) {
            alert('Please select or create a chat first');
            return;
        }
        if (!selectedVaultId) {
            alert('Please select a vault first');
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
            console.log('=== Received API response ===');
            console.log('Full response:', data);
            console.log('Message ID from DB:', assistantMessageId);
            console.log('Fragments count:', data.fragments?.length || 0);
            console.log('Fragments data:', data.fragments);
            
            // Сохраняем fragments с ID из БД (и как string, и как number для совместимости)
            if (data.fragments && data.fragments.length > 0) {
                console.log('✓ Saving fragments for message ID:', assistantMessageId, '(type:', typeof assistantMessageId, ')', 'fragments:', data.fragments);
                setMessageFragments(prev => {
                    const newMap = new Map(prev);
                    // Сохраняем и как number, и как string для совместимости
                    newMap.set(assistantMessageId, data.fragments);
                    newMap.set(String(assistantMessageId), data.fragments);
                    console.log('New fragments map:', Array.from(newMap.entries()).map(([k, v]) => [`${k}(${typeof k})`, v.length]));
                    return newMap;
                });
            } else {
                console.warn('✗ No fragments in response!');
            }
            
            // Добавляем сообщение с ID из БД
            setMessages(messages => [...messages, {
                role: "assistant",
                content: data.answer,
                datetime: new Date().toISOString(),
                id: assistantMessageId
            }]);
            setRelatedDocuments(() => data.related_documents);
        }, (reason) => {
            console.error('Error sending message:', reason);
            // Удаляем сообщение пользователя при ошибке
            setMessages(messages => messages.slice(0, -1));
        });
    };

    const sendCombinedSearchWrapper = () => {
        if (!userCurrentMessage.trim()) return;
        if (!chatId) {
            alert('Please select or create a chat first');
            return;
        }
        if (!selectedVaultId) {
            alert('Please select a vault first');
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

        sendCombinedSearch({
            content: messageContent,
            chat_id: chatId,
            vault_id: selectedVaultId
        }).then((data) => {
            const assistantMessageId = data.message_id;
            console.log('=== Received Combined Search API response ===');
            console.log('Full response:', data);
            console.log('Message ID from DB:', assistantMessageId);
            console.log('Fragments count:', data.fragments?.length || 0);
            
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
        }, (reason) => {
            console.error('Error sending combined search message:', reason);
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
    const availableVaults = vaultsData?.vaults || [];

    return (
        <BasicLayout>
            <div className="chat-container">
                <Flex direction={"row"} h="100%" gap={0}>
                    {/* Sidebar с чатами - Desktop */}
                    <div className="chat-sidebar">
                        <Stack gap="sm">
                            <Group justify="space-between">
                                <Text size="sm" fw={600}>Chats</Text>
                                <Button
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconPlus size={14} />}
                                    onClick={handleCreateChat}
                                    loading={isCreateChatPending}
                                    disabled={!selectedVaultId || availableVaults.length === 0}
                                >
                                    New
                                </Button>
                            </Group>
                            
                            <Select
                                label="Vault"
                                placeholder="Select vault"
                                data={availableVaults.map(v => ({ value: v.id.toString(), label: v.name }))}
                                value={selectedVaultId?.toString() || null}
                                onChange={(value) => setSelectedVaultId(value ? parseInt(value) : null)}
                                disabled={vaultsLoading || availableVaults.length === 0}
                            />

                            <ScrollArea scrollbars="y" h={400}>
                                <Stack gap="xs">
                                    {chatsLoading ? (
                                        <Loader size="sm" />
                                    ) : availableChats.length === 0 ? (
                                        <Text size="sm" c="dimmed">No chats yet</Text>
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
                        title="Chats"
                        position="left"
                        padding="md"
                        size="xs"
                        className="mobile-chats-drawer"
                    >
                        <Stack gap="sm">
                            <Group justify="space-between">
                                <Text size="sm" fw={600}>Chats</Text>
                                <Button
                                    size="xs"
                                    variant="light"
                                    leftSection={<IconPlus size={14} />}
                                    onClick={handleCreateChat}
                                    loading={isCreateChatPending}
                                    disabled={!selectedVaultId || availableVaults.length === 0}
                                >
                                    New
                                </Button>
                            </Group>
                            
                            <Select
                                label="Vault"
                                placeholder="Select vault"
                                data={availableVaults.map(v => ({ value: v.id.toString(), label: v.name }))}
                                value={selectedVaultId?.toString() || null}
                                onChange={(value) => {
                                    setSelectedVaultId(value ? parseInt(value) : null);
                                    closeChatsDrawer();
                                }}
                                disabled={vaultsLoading || availableVaults.length === 0}
                            />

                            <ScrollArea scrollbars="y" h={400}>
                                <Stack gap="xs">
                                    {chatsLoading ? (
                                        <Loader size="sm" />
                                    ) : availableChats.length === 0 ? (
                                        <Text size="sm" c="dimmed">No chats yet</Text>
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
                                aria-label="Open chats"
                            >
                                <IconMenu2 size={20} />
                            </ActionIcon>
                            <Text size="sm" fw={500}>
                                {chatId ? availableChats.find(c => c.id === chatId)?.title || 'Chat' : 'RAG Chat'}
                            </Text>
                            <ActionIcon
                                variant="light"
                                onClick={toggleInfoDrawer}
                                size="lg"
                                aria-label="Open info"
                            >
                                <IconInfoHexagonFilled size={20} />
                            </ActionIcon>
                        </div>

                        {!chatId ? (
                            <div className="chat-empty-state">
                                <Text size="lg" c="dimmed">Select a chat or create a new one</Text>
                                <Button
                                    onClick={handleCreateChat}
                                    loading={isCreateChatPending}
                                    disabled={!selectedVaultId || availableVaults.length === 0}
                                    leftSection={<IconPlus size={16} />}
                                >
                                    Create New Chat
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
                                        <MessageHistory 
                                            messages={messages} 
                                            isAssistantThinking={isSendMessagePending || isCombinedSearchPending}
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
                                            placeholder="Message..."
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
                                        <ActionIcon
                                            loaderProps={{ type: "oval" }}
                                            loading={isCombinedSearchPending}
                                            size={42}
                                            radius="md"
                                            color="green"
                                            variant="light"
                                            onClick={sendCombinedSearchWrapper}
                                            disabled={!selectedVaultId || !userCurrentMessage.trim()}
                                            title="Комбинированный поиск (Obsidian + Yandex)"
                                        >
                                            <IconSearch style={{ width: 20, height: 20 }} stroke={2} />
                                        </ActionIcon>
                                        <ActionIcon
                                            loaderProps={{ type: "oval" }}
                                            loading={isSendMessagePending}
                                            size={42}
                                            radius="md"
                                            color="blue"
                                            variant="filled"
                                            onClick={sendMessageWrapper}
                                            disabled={!selectedVaultId || !userCurrentMessage.trim()}
                                            title="Отправить сообщение"
                                        >
                                            <IconArrowRight style={{ width: 20, height: 20 }} stroke={2} />
                                        </ActionIcon>
                                    </Flex>
                                </div>
                            </>
                        )}
                    </Flex>

                    {/* Правая панель с информацией - Desktop */}
                    <div className="chat-info-sidebar">
                        <Accordion multiple={true} defaultValue={["General"]} variant="default">
                            <Accordion.Item value={"General"}>
                                <Accordion.Control icon={<IconInfoHexagonFilled size={18} />}>
                                    <Text size="sm" fw={500}>General</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    <Stack gap="xs">
                                        <div>
                                            <Text size="xs" c="dimmed">In-Tokens</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.input_tokens : "—"}</Text>
                                        </div>
                                        <div>
                                            <Text size="xs" c="dimmed">Out-Tokens</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.output_tokens : "—"}</Text>
                                        </div>
                                    </Stack>
                                </Accordion.Panel>
                            </Accordion.Item>
                            <Accordion.Item value={"Related"}>
                                <Accordion.Control icon={<IconBookmarksFilled size={18} />}>
                                    <Text size="sm" fw={500}>Related documents</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    {relatedDocuments.length === 0 ? (
                                        <Text size="sm" c="dimmed">No documents</Text>
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
                            <Accordion.Item value={"Management"}>
                                <Accordion.Control icon={<IconSettingsFilled size={18} />}>
                                    <Text size="sm" fw={500}>Management</Text>
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
                                        Clear history
                                    </Button>
                                </Accordion.Panel>
                            </Accordion.Item>
                        </Accordion>
                    </div>

                    {/* Mobile Drawer для информации */}
                    <Drawer
                        opened={infoDrawerOpened}
                        onClose={closeInfoDrawer}
                        title="Info"
                        position="right"
                        padding="md"
                        size="xs"
                        className="mobile-info-drawer"
                    >
                        <Accordion multiple={true} defaultValue={["General"]} variant="default">
                            <Accordion.Item value={"General"}>
                                <Accordion.Control icon={<IconInfoHexagonFilled size={18} />}>
                                    <Text size="sm" fw={500}>General</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    <Stack gap="xs">
                                        <div>
                                            <Text size="xs" c="dimmed">In-Tokens</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.input_tokens : "—"}</Text>
                                        </div>
                                        <div>
                                            <Text size="xs" c="dimmed">Out-Tokens</Text>
                                            <Text size="sm" fw={500}>{isLLMTokensSuccess ? llmTokens.output_tokens : "—"}</Text>
                                        </div>
                                    </Stack>
                                </Accordion.Panel>
                            </Accordion.Item>
                            <Accordion.Item value={"Related"}>
                                <Accordion.Control icon={<IconBookmarksFilled size={18} />}>
                                    <Text size="sm" fw={500}>Related documents</Text>
                                </Accordion.Control>
                                <Accordion.Panel>
                                    {relatedDocuments.length === 0 ? (
                                        <Text size="sm" c="dimmed">No documents</Text>
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
                            <Accordion.Item value={"Management"}>
                                <Accordion.Control icon={<IconSettingsFilled size={18} />}>
                                    <Text size="sm" fw={500}>Management</Text>
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
                                        Clear history
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
