import {MessageSchema, FragmentInfo} from "../../types/messages"
import Markdown from "react-markdown";
import remarkGfm from 'remark-gfm';
import {Prism as SyntaxHighlighter} from 'react-syntax-highlighter'
import {oneDark} from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Loader } from '@mantine/core';
import { useState, useRef, useEffect } from 'react';
import "./index.css";

const MARKDOWN_STYLES = {
    code: ({...props}: any) => {
        const {children, className, node, ...rest} = props
        const match = /language-(\w+)/.exec(className || '')
        return match ? (
          <SyntaxHighlighter
            {...rest}
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
    img: ({...props}: any) => {
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
    table: ({...props}: any) => {
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
    const className = `message ${props.message.role}-message`
    const [selectedFragment, setSelectedFragment] = useState<FragmentInfo | null>(null);
    const contentRef = useRef<HTMLDivElement>(null);

    // Обработка выделения текста - улучшенная версия
    useEffect(() => {
        if (props.message.role !== 'assistant' || !props.fragments || props.fragments.length === 0) {
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

            for (const fragment of props.fragments!) {
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
                        if (props.onFragmentClick) {
                            props.onFragmentClick(bestMatch, props.message.id);
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
    }, [props.message, props.fragments, props.onFragmentClick]);

    // Показываем источники для сообщений ассистента с fragments
    const hasFragments = props.fragments && props.fragments.length > 0 && props.message.role === 'assistant';

    return (
        <div className={className} ref={contentRef}>
            {
              props.isLoading
              ? <Loader color="blue" type="dots" size="sm"/>
              : (
                <>
                    <Markdown 
                      remarkPlugins={[remarkGfm]} 
                      children={props.message.content} 
                      className="reactMarkDown"
                      components={MARKDOWN_STYLES}
                    />
                    {hasFragments && (
                        <div className="message-sources">
                            <span className="message-sources-label">Источники:</span>
                            <div className="message-sources-list">
                                {props.fragments!.map((fragment, index) => (
                                    <span
                                        key={index}
                                        className={`message-source-item ${selectedFragment?.filename === fragment.filename ? 'active' : ''}`}
                                        onClick={() => {
                                            setSelectedFragment(fragment);
                                            if (props.onFragmentClick) {
                                                props.onFragmentClick(fragment, props.message.id);
                                            }
                                        }}
                                    >
                                        {fragment.filename} ({fragment.similarity.toFixed(2)})
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                    {selectedFragment && (
                        <div className="fragment-hint">
                            <strong>Выбранный источник:</strong> {selectedFragment.filename} (similarity: {selectedFragment.similarity.toFixed(2)})
                        </div>
                    )}
                </>
              )
            }
        </div>
    );
}
export default Message;