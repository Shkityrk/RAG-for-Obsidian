import {MessageSchema, FragmentInfo} from "../../types/messages"
import Markdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from 'remark-gfm';
import {Prism as SyntaxHighlighter} from 'react-syntax-highlighter'
import {oneDark} from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Loader } from '@mantine/core';
import { useState, useRef, useEffect } from 'react';
import "./index.css";

const MARKDOWN_STYLES: Components = {
    code: ({children, className, ...rest}) => {
        const match = /language-(\w+)/.exec(className || '')
        return match ? (
          <SyntaxHighlighter
            PreTag="div"
            children={String(children).replace(/\n$/, '')}
            language={match[1]}
            style={oneDark}
            customStyle={{
                margin: '16px 0',
                borderRadius: '8px',
                fontSize: '14px',
                lineHeight: '1.5'
            }}
          />
        ) : (
          <code {...rest} className={className}>
            {children}
          </code>
        )
      },
    img: ({...props}) => {
        const {src, alt, ...rest} = props;
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
              margin: '20px auto'
            }}
          />
        );
      },
    table: ({...props}) => {
        return (
          <div style={{ 
            overflowX: 'auto', 
            margin: '16px 0',
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
}


export interface MessageProps  {
    message: MessageSchema,
    isLoading: boolean,
    fragments?: FragmentInfo[],
    vaultId?: number,
    onFragmentClick?: (fragment: FragmentInfo, messageId: number | string) => void
}


const Message = (props: MessageProps) => {
    const { message, isLoading, fragments, onFragmentClick } = props;
    const className = `message ${message.role}-message`
    const [selectedFragment, setSelectedFragment] = useState<FragmentInfo | null>(null);
    const contentRef = useRef<HTMLDivElement>(null);

    // Обработка выделения текста - улучшенная версия
    useEffect(() => {
        if (message.role !== 'assistant' || !fragments || fragments.length === 0) {
            return;
        }

        const handleMouseUp = () => {
            const selection = window.getSelection();
            if (!selection || selection.toString().trim().length === 0) {
                return;
            }

            const selectedText = selection.toString().trim();
            // Берем первые 100 символов для поиска
            const searchText = selectedText.substring(0, 100).toLowerCase();
            
            if (searchText.length < 10) {
                // Слишком короткий текст для поиска
                return;
            }

            // Ищем фрагмент, который наиболее похож на выделенный текст
            let bestMatch: FragmentInfo | null = null;
            let bestScore = 0;

            for (const fragment of fragments) {
                const fragmentText = fragment.text.toLowerCase();
                // Проверяем, содержит ли фрагмент выделенный текст
                if (fragmentText.includes(searchText)) {
                    // Вычисляем "score" на основе длины совпадения и similarity
                    const matchLength = Math.min(searchText.length, fragmentText.length);
                    const score = matchLength * fragment.similarity;
                    if (score > bestScore) {
                        bestScore = score;
                        bestMatch = fragment;
                    }
                }
            }

                    if (bestMatch) {
                        setSelectedFragment(bestMatch);
                        if (onFragmentClick) {
                            onFragmentClick(bestMatch, message.id);
                        }
                    }
        };

        // Слушаем события на всем документе, но проверяем, что клик был внутри нашего компонента
        const handleDocumentMouseUp = (e: MouseEvent) => {
            if (contentRef.current && contentRef.current.contains(e.target as Node)) {
                // Небольшая задержка, чтобы selection успел обновиться
                setTimeout(handleMouseUp, 10);
            }
        };

        document.addEventListener('mouseup', handleDocumentMouseUp);
        return () => {
            document.removeEventListener('mouseup', handleDocumentMouseUp);
        };
    }, [message, fragments, onFragmentClick]);

    // Показываем источники для сообщений ассистента с fragments
    const hasFragments = fragments && fragments.length > 0 && message.role === 'assistant';

    return (
        <div className={className} ref={contentRef}>
            {
              isLoading
              ? <Loader color="blue" type="dots" size="sm"/>
              : (
                <>
                    <Markdown 
                      remarkPlugins={[remarkGfm]} 
                      children={message.content}
                      className="reactMarkDown"
                      components={MARKDOWN_STYLES}
                    />
                    {hasFragments && (
                        <div className="message-sources">
                            <span className="message-sources-label">Источники</span>
                            <div className="message-sources-list">
                                {fragments.map((fragment, index) => (
                                    <button
                                        key={index}
                                        type="button"
                                        className={`message-source-item ${selectedFragment?.filename === fragment.filename ? 'active' : ''}`}
                                        onClick={() => {
                                            setSelectedFragment(fragment);
                                            if (onFragmentClick) {
                                                onFragmentClick(fragment, message.id);
                                            }
                                        }}
                                    >
                                        {fragment.filename} ({fragment.similarity.toFixed(2)})
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                    {selectedFragment && (
                        <div className="fragment-hint">
                            <strong>Выбранный источник:</strong> {selectedFragment.filename} ({selectedFragment.similarity.toFixed(2)})
                        </div>
                    )}
                </>
              )
            }
        </div>
    );
}
export default Message;
