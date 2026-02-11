import { useState, useEffect, useMemo } from 'react';
import { ScrollArea, Paper, Text, Loader, Stack, Group, CloseButton } from '@mantine/core';
import { vaultsApi } from '../../api/vaults';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FragmentInfo } from '../../types/messages';
import './index.css';

interface DocumentViewerProps {
    vaultId: number;
    filename: string;
    fragments?: FragmentInfo[]; // Все фрагменты для подсветки
    onClose?: () => void;
}

const MARKDOWN_STYLES = {
    code: ({ ...props }: any) => {
        const { children, className, node, ...rest } = props;
        const match = /language-(\w+)/.exec(className || '');
        return match ? (
            <SyntaxHighlighter
                {...rest}
                PreTag="div"
                children={String(children).replace(/\n$/, '')}
                language={match[1]}
                style={oneDark}
                customStyle={{
                    margin: '20px 0',
                    borderRadius: '8px',
                    fontSize: '14px',
                    lineHeight: '1.5'
                }}
            />
        ) : (
            <code {...rest} className={className}>
                {children}
            </code>
        );
    },
    img: ({ ...props }: any) => {
        const { src, alt, ...rest } = props;
        return (
            <img
                {...rest}
                src={src}
                alt={alt || 'Image'}
                loading="lazy"
                style={{
                    maxWidth: '100%',
                    height: 'auto',
                    display: 'block',
                    margin: '24px auto'
                }}
            />
        );
    },
    table: ({ ...props }: any) => {
        return (
            <div style={{ 
                overflowX: 'auto', 
                margin: '20px 0',
                width: '100%',
                WebkitOverflowScrolling: 'touch'
            }}>
                <table {...props} style={{ 
                    width: '100%',
                    borderCollapse: 'collapse',
                    margin: 0
                }} />
            </div>
        );
    },
};

const DocumentViewer = ({ vaultId, filename, fragments = [], onClose }: DocumentViewerProps) => {
    const [content, setContent] = useState<string>('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Фильтруем фрагменты для текущего файла
    const fileFragments = useMemo(() => {
        return fragments.filter(f => f.filename === filename);
    }, [fragments, filename]);

    // Функция для выделения фрагментов в тексте перед рендерингом Markdown
    const highlightedContent = useMemo(() => {
        if (!content || fileFragments.length === 0) {
            return content;
        }

        let result = content;
        
        // Сортируем фрагменты по длине текста (от большего к меньшему)
        const sortedFragments = [...fileFragments].sort((a, b) => b.text.length - a.text.length);
        
        // Выделяем каждый фрагмент
        for (const fragment of sortedFragments) {
            const fragmentText = fragment.text.trim();
            if (fragmentText.length < 10) continue;
            
            // Экранируем специальные символы для regex
            const escapedText = fragmentText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            
            // Находим все совпадения и заменяем их в обратном порядке (с конца)
            const matches: Array<{ index: number; text: string }> = [];
            
            // Используем matchAll для поиска всех совпадений
            const regex = new RegExp(escapedText, 'gi');
            const allMatches = Array.from(result.matchAll(regex));
            
            for (const match of allMatches) {
                if (match.index === undefined) continue;
                
                const index = match.index;
                const matchedText = match[0];
                
                // Проверяем, не находится ли совпадение внутри уже выделенного текста
                const beforeMatch = result.substring(Math.max(0, index - 200), index);
                const openMarks = (beforeMatch.match(/<mark[^>]*>/g) || []).length;
                const closeMarks = (beforeMatch.match(/<\/mark>/g) || []).length;
                
                if (openMarks <= closeMarks) {
                    // Не внутри выделения - добавляем в список для замены
                    matches.push({ index, text: matchedText });
                }
            }
            
            // Заменяем совпадения в обратном порядке (с конца), чтобы индексы не менялись
            for (let i = matches.length - 1; i >= 0; i--) {
                const { index, text } = matches[i];
                const before = result.substring(0, index);
                const after = result.substring(index + text.length);
                const highlighted = `<mark class="highlight-fragment" data-similarity="${fragment.similarity.toFixed(2)}">${text}</mark>`;
                result = before + highlighted + after;
            }
        }
        
        return result;
    }, [content, fileFragments]);

    useEffect(() => {
        const loadFile = async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await vaultsApi.getFile(vaultId, filename);
                setContent(data.content);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load file');
            } finally {
                setLoading(false);
            }
        };

        if (vaultId && filename) {
            loadFile();
        }
    }, [vaultId, filename]);

    if (loading) {
        return (
            <Paper p="md" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Stack align="center" gap="sm">
                    <Loader size="md" />
                    <Text size="sm" c="dimmed">Loading document...</Text>
                </Stack>
            </Paper>
        );
    }

    if (error) {
        return (
            <Paper p="md" style={{ height: '100%' }}>
                <Stack gap="sm">
                    <Group justify="space-between">
                        <Text size="sm" fw={500}>Error</Text>
                        {onClose && <CloseButton onClick={onClose} />}
                    </Group>
                    <Text size="sm" c="red">{error}</Text>
                </Stack>
            </Paper>
        );
    }

    return (
        <Paper p="md" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Stack gap="sm" style={{ flex: 1, overflow: 'hidden' }}>
                <Group justify="space-between">
                    <Text size="sm" fw={500} truncate style={{ maxWidth: '80%' }}>
                        {filename}
                    </Text>
                    {onClose && <CloseButton onClick={onClose} />}
                </Group>
                
                <ScrollArea style={{ flex: 1 }}>
                    <div className="document-content">
                        {fileFragments.length > 0 && (
                            <div style={{ 
                                marginBottom: '12px', 
                                padding: '8px 12px', 
                                backgroundColor: 'rgba(255, 235, 59, 0.2)',
                                borderLeft: '3px solid #ffc107',
                                borderRadius: '4px',
                                fontSize: '12px'
                            }}>
                                <Text size="xs" fw={500} mb={4}>
                                    Найдено релевантных фрагментов: {fileFragments.length}
                                </Text>
                                <Text size="xs" c="dimmed">
                                    Фрагменты выделены жёлтым цветом в тексте ниже
                                </Text>
                            </div>
                        )}
                        <Markdown 
                            remarkPlugins={[remarkGfm]} 
                            rehypePlugins={[rehypeRaw]}
                            components={MARKDOWN_STYLES}
                        >
                            {highlightedContent}
                        </Markdown>
                    </div>
                </ScrollArea>
            </Stack>
        </Paper>
    );
};

export default DocumentViewer;

