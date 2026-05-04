import {Stack} from '@mantine/core';
import {MessageSchema, FragmentInfo} from "../../types/messages"
import Message from "./../message"


export interface MessageHistoryProps  {
  messages: Array<MessageSchema>,
  isAssistantThinking: boolean,
  messageFragments?: Map<string | number, FragmentInfo[]>,
  vaultId?: number,
  onFragmentClick?: (fragment: FragmentInfo, messageId: number | string) => void
}

const assistantThinkingMessage: MessageSchema = {
  id: 'thinking',
  role: 'assistant',
  content: 'Думаю...',
  datetime: new Date().toISOString()
}

const MessageHistory = (props: MessageHistoryProps) => {
  return (
    <Stack h="100%" gap="md" style={{maxWidth: '768px', margin: '0 auto', width: '100%', padding: '0 16px'}}>
        {
          props.messages.map(message => {
            // Пробуем найти fragments по разным типам ID (string или number)
            // Преобразуем ID сообщения в строку и число для поиска
            const messageIdStr = String(message.id);
            const messageIdNum = Number(message.id);
            
            // Пробуем найти по всем возможным вариантам ключа
            let fragments = props.messageFragments?.get(message.id);
            if (!fragments) fragments = props.messageFragments?.get(messageIdStr);
            if (!fragments) fragments = props.messageFragments?.get(messageIdNum);
            
            // Также пробуем найти по всем ключам в Map, сравнивая значения
            if (!fragments && props.messageFragments) {
              for (const [key, value] of props.messageFragments.entries()) {
                const keyStr = String(key);
                const keyNum = Number(key);
                if (keyStr === messageIdStr || keyNum === messageIdNum || 
                    String(key) === String(message.id) || Number(key) === Number(message.id)) {
                  fragments = value;
                  break;
                }
              }
            }
            
            return (
              <Message 
                key={message.id} 
                isLoading={false} 
                message={message}
                fragments={fragments}
                vaultId={props.vaultId}
                onFragmentClick={props.onFragmentClick}
              />
            );
          })
        }
        {
          props.isAssistantThinking && <Message isLoading={props.isAssistantThinking} message={assistantThinkingMessage}/>
        }
    </Stack>
    );
}
export default MessageHistory;
