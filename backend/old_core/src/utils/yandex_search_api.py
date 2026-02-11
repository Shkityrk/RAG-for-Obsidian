"""
1. в волте нет инфы о такой то хуйне, ворзьмем запрос пользователя и найдем, а что же нам искать?
пусть llm предложит нам от 1 до 5 запросов для поиска

2. делаем поиск для каждого из запросов предложенных
3. вычленяем информацию: из каждого из запросов парсим поля: headline, extended-text, внутри них убираем все теги
4. задаем генеративный запрос для получения ответа
5. собираем контекст: запросы после предобработки(все символы аля \n меняем на /n, сами enter меняем на \n) +
генеративный ответ
6. ждем ответ от llmки, и выводим его с пояснением, мол в vault нихуя не нашлось, но вот что говорит инет


! мб генеративный ответ должен иметь влияние , но это не точно


# генеративный контент яндекса
https://searchapi.api.cloud.yandex.net/v2/gen/search
{
  "messages": [
    {
      "content": "как снять усталость?",
      "role": "ROLE_USER"
    }
  ],
  "searchType": "SEARCH_TYPE_RU",
  "folderId": "b1gei2a4l5v7osh4grp9",
  "fixMisspell": true,
  "getPartialResults": false
}



# посик от яндекса
https://searchapi.api.cloud.yandex.net/v2/web/search post
{
  "query": {
    "searchType": "SEARCH_TYPE_RU",
    "queryText": "списки в python",
    "fixTypoMode": "FIX_TYPO_MODE_ON"
  },
  "groupSpec": {
    "groupMode": "GROUP_MODE_DEEP",
    "groupsOnPage": "4",
    "docsInGroup": "3"
  },
  "folderId": "b1gei2a4l5v7osh4grp9",
  "responseFormat": "FORMAT_XML",
  "userAgent": "Mozilla/5.0 (compatible; RAGBot/1.0)"
}



# запросы к ollama
http://localhost:11434/api/generate
{
  "model": "gpt-oss:20b",
  "prompt": "СИСТЕМА: Отвечай только на основе фрагментов ниже, ответь точно на поставленный вопрос.\n\nИНСТРУКЦИЯ: Есть вопрос и релевантные ответы. На их основе ответь кратко.\n\nВОПРОС: уравнение аррениуса в интегральном виде\n\nОТВЕТЫ:\n[1] (Интегральная форма уравнения Аррениуса). Для одностадийных реакций\nпредэкспоненциальный множитель имеет простой физический смысл – отражает вероятность\nвзаимодействия молекул, обладающих необходимой энергией. имеет вероятностную, т.е.\nэнтропийную природу, связанную с пространственными факторами взаимодействия и элементами\nсимметрии; - для мономолекулярных газовых реакций это частота колебаний разрываемой\nсвязи вдоль пути реакции (для бимолекулярных реакций – частота межмолекулярных\nстолкновений). В соответствии с уравнением Аррениуса: чем меньше , тем больше k и\nскорость химической реакции. Чем выше , тем сильнее k и W зависят от температуры.\nЗначения Находят на основании зависимости k реакции от температуры. Строят график в\nкоординатах: ̶ (координаты Аррениуса). График!!! Тангенс угла наклона.\nТЕРМОДИНАМИЧЕСКИЙ ВЫВОД УРАВНЕНИЯ АРРЕНИУСА. – уравнение изохоры Вант-Гоффа.\n– константа равновесия химической реакции, есть отношение констант скоростей прямой и\nобратной реакций. ; , тогда ; . В общем случае получим уравнение Аррениуса в\nдифференциальной форме: Проинтегрируем по температуре: Если энергия активации не зависит\nот температуры ( ), то получим: Обозначим , получим уравнение Аррениуса в интегральной\nформе: Преобразуем это уравнение и получим уравнение Аррениуса в экспоненциальной форме:\nОПРЕДЕЛЕНИЕ ЭНЕРГИИ АКТИВАЦИИ. Так как в уравнение Аррениуса входят две неизвестные\nвеличины (k и E), для нахождения этих величин мы должны составить, как минимум, два\nуравнения, т. е. нам необходимо знать значения двух констант скоростей при двух\nтемпературах. (2 при 2Т)! Существует 2 способа определения энергии активации.\n[2] Уравнение Аррениуса. Е. стр. 66-74, Э.-К. стр. 73-77, Р. стр. 89-95. Аррениус\nпредложил уравнение для описания экспериментальной температурной зависимости константы\nскорости химической реакции: d ln k dT. = EA RT 2. (1). Здесь EA - опытная (т.е.\nопределяемая в эксперименте!) или аррениусовская энергия. активации. Интегральная форма\nуравнения имеет вид: lnk = lnA - EA/RT. или. k = A e- EA/RT. (2) (3). При переходе к (2)\nи (3) предполагается, что энергия активации и предэкспоненциальный множитель A не\nзависят от температуры во всяком случае в исследуемом температурном интервале.\nЭкспериментальная зависимость ln k = f (1/T) показана на рис.1. 1.\n[3] Здесь EA - опытная (т.е. определяемая в эксперименте!) или аррениусовская\nэнергия. активации. Интегральная форма уравнения имеет вид: lnk = lnA - EA/RT. или. k =\nA e- EA/RT. (2) (3). При переходе к (2) и (3) предполагается, что энергия активации и\nпредэкспоненциальный множитель A не зависят от температуры, во всяком случае в\nисследуемом температурном интервале. Экспериментальная зависимость ln k = f (1/T)\nпоказана на рис.1. 1.\n[4] \n5.1 Arrhenius&#39;s concept of activation energy. 5.2 Collision theory. 5.3 Transition\nstate theory. 5.4 Limitations of the idea of Arrhenius activation energy. Alternatively, the\nequation may be expressed as. k = A e − E a k. B. T = A exp ⁡ ( − E a k. B. T ) ,\n{/displaystyle k=Ae^{/frac {-E_{/mathrm {a} }}{k_{/text{B}}T}}=A/exp {/left({/frac\n{-E_{/mathrm {a} }}{k_{/text{B}}T}}/right)},} {/displaystyle k=Ae^{/frac {-E_{/mathrm {a}\n}}{k_{/text{B}}T}}=A/exp {/left({/frac {-E_{/mathrm {a} }}{k_{/text{B}}T}}/right)},} where.\n\n\nОТВЕТЬ ТОЛЬКО НА ОСНОВЕ ЭТОГО.\n",
  "stream": false,
  "options": {"num_ctx": 16384}
}


СИСТЕМА: Ты химик. Отвечай только на основе фрагментов ниже.

ИНСТРУКЦИЯ: Есть вопрос и релевантные ответы. На их основе ответь кратко.

ВОПРОС: уравнение аррениуса в интегральном виде

ОТВЕТЫ:
[1] Интегральная форма уравнения Аррениуса: lnk = lnA - EA/RT или k = A e^(-EA/RT)...
[2] d ln k / dT = EA / RT^2. Интегральная форма: lnk = lnA - EA/RT...
[3] ... (вставьте все ваши фрагменты)

ОТВЕТЬ ТОЛЬКО НА ОСНОВЕ ЭТОГО.

"""


import requests
import json
import base64
import re
import asyncio
import logging
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
from src.config import app_config


content = "Что такое CRUD? Примеры задач, демонстрирующих необходимость использования дополнительных глаголов HTTP." # запрос который получили


def get_yandex_auth_token() -> str:
    """Получает токен авторизации Yandex из конфига."""
    token = app_config.YANDEX_AUTH_TOKEN
    if not token:
        raise ValueError("YANDEX_AUTH_TOKEN не установлен в конфигурации")
    # Если токен не начинается с "Bearer ", добавляем его
    if not token.startswith("Bearer "):
        return f"Bearer {token}"
    return token


def get_yandex_folder_id() -> str:
    """Получает folder ID Yandex из конфига."""
    folder_id = app_config.YANDEX_FOLDER_ID
    if not folder_id:
        raise ValueError("YANDEX_FOLDER_ID не установлен в конфигурации")
    return folder_id


def get_ollama_url() -> str:
    """Получает полный URL для Ollama API."""
    base_url = app_config.OLLAMA_BASE_URL.rstrip("/")
    return f"{base_url}/api/generate"

ollama_model = app_config.LLM_MODEL

# ================== запросы и инструкции к llm и тп ==================

PROMPT_GENERATE_SEARCH_QUERIES = """СИСТЕМА: Ты помощник для генерации поисковых запросов.

ИНСТРУКЦИЯ: Пользователь задал вопрос, для которого нет информации в базе знаний. 
Сгенерируй от 1 до 5 поисковых запросов для поисковой системы, которые помогут найти ответ на этот вопрос.
Запросы должны быть конкретными и максимально правильно отражать суть вопроса, но так, чтобы ответ на этот вопрос был найден в поисковой системе.
Выведи каждый запрос с новой строки, без нумерации и дополнительных символов.

ВОПРОС: {user_query}

ПОИСКОВЫЕ ЗАПРОСЫ:"""

PROMPT_FINAL_ANSWER = """СИСТЕМА: Отвечай только на основе фрагментов ниже, ответь точно на поставленный вопрос.

ИНСТРУКЦИЯ: Есть вопрос и релевантные ответы. На их основе ответь кратко.

ВОПРОС: {user_query}

ОТВЕТЫ:
{context}

ОТВЕТЬ ТОЛЬКО НА ОСНОВЕ ЭТОГО."""

# ================== код ==================


def generate_search_queries(user_query: str) -> List[str]:
    """
    Генерирует от 1 до 5 поисковых запросов через Ollama.
    
    Args:
        user_query: Исходный запрос пользователя
        
    Returns:
        Список поисковых запросов
    """
    prompt = PROMPT_GENERATE_SEARCH_QUERIES.format(user_query=user_query)
    
    payload = {
        "model": ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 16384}
    }
    
    try:
        response = requests.post(get_ollama_url(), json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Извлекаем сгенерированные запросы из ответа
        generated_text = result.get("response", "").strip()
        
        # Разбиваем на отдельные запросы (каждый с новой строки)
        queries = [q.strip() for q in generated_text.split("\n") if q.strip()]
        
        # Ограничиваем до 5 запросов
        queries = queries[:5]
        print(queries)
        
        return queries if queries else [user_query]
    except Exception as e:
        print(f"Ошибка при генерации запросов: {e}")
        return [user_query]


def search_yandex(query: str) -> str:
    """
    Выполняет поиск в Яндексе для заданного запроса.
    
    Ответ от Яндекса приходит в виде JSON с полем rawData, содержащим base64-закодированный XML.
    
    Args:
        query: Поисковый запрос
        
    Returns:
        XML ответ от Яндекс Поиска (декодированный из base64)
    """
    url = "https://searchapi.api.cloud.yandex.net/v2/web/search"
    
    payload = {
        "query": {
            "searchType": "SEARCH_TYPE_RU",
            "queryText": query,
            "fixTypoMode": "FIX_TYPO_MODE_ON"
        },
        "groupSpec": {
            "groupMode": "GROUP_MODE_DEEP",
            "groupsOnPage": "4",
            "docsInGroup": "3"
        },
        "folderId": get_yandex_folder_id(),
        "responseFormat": "FORMAT_XML",
        "userAgent": "Mozilla/5.0 (compatible; RAGBot/1.0)"
    }
    
    headers = {
        "Authorization": get_yandex_auth_token(),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        # Ответ приходит в виде JSON с полем rawData, содержащим base64
        response_json = response.json()
        
        # Извлекаем rawData из ответа
        # Может быть в корне или в response.rawData
        raw_base64 = None
        if "rawData" in response_json:
            raw_base64 = response_json["rawData"]
        elif "response" in response_json and isinstance(response_json["response"], dict):
            if "rawData" in response_json["response"]:
                raw_base64 = response_json["response"]["rawData"]
        
        if not raw_base64:
            print("Предупреждение: поле rawData не найдено в ответе Яндекса")
            # Пытаемся вернуть весь ответ как есть (на случай другого формата)
            return response.text
        
        # Декодируем base64
        try:
            decoded_bytes = base64.b64decode(raw_base64)
            # Преобразуем в строку UTF-8
            xml_content = decoded_bytes.decode('utf-8')
            return xml_content
        except Exception as decode_error:
            print(f"Ошибка при декодировании base64: {decode_error}")
            return ""
        
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON от Яндекса: {e}")
        # Если не JSON, возвращаем как есть
        return response.text
    except Exception as e:
        print(f"Ошибка при поиске в Яндексе: {e}")
        return ""


def parse_search_results(xml_content: str) -> List[Dict[str, str]]:
    """
    Парсит результаты поиска, извлекает headline и extended-text, убирает все теги.
    
    Структура XML от Яндекса:
    <yandexsearch>
      <response>
        <results>
          <grouping>
            <group>
              <doc>
                <headline>...</headline>
                <properties>
                  <extended-text>...</extended-text>
                </properties>
              </doc>
            </group>
          </grouping>
        </results>
      </response>
    </yandexsearch>
    
    Args:
        xml_content: XML ответ от Яндекс Поиска
        
    Returns:
        Список словарей с полями headline и extended-text
    """
    if not xml_content:
        return []
    
    results = []
    
    try:
        root = ET.fromstring(xml_content)
        
        # Ищем все элементы <doc> в XML
        for doc in root.findall(".//doc"):
            result_item = {}
            
            # Ищем headline напрямую в doc
            headline_elem = doc.find("headline")
            if headline_elem is not None:
                headline_text = headline_elem.text if headline_elem.text else ""
                # Также собираем текст из всех дочерних элементов
                if not headline_text:
                    headline_text = "".join(headline_elem.itertext())
                if headline_text:
                    result_item["headline"] = remove_html_tags(headline_text.strip())
            
            # Ищем extended-text внутри properties
            properties = doc.find("properties")
            if properties is not None:
                extended_text_elem = properties.find("extended-text")
                if extended_text_elem is not None:
                    extended_text = extended_text_elem.text if extended_text_elem.text else ""
                    # Также собираем текст из всех дочерних элементов
                    if not extended_text:
                        extended_text = "".join(extended_text_elem.itertext())
                    if extended_text:
                        result_item["extended-text"] = remove_html_tags(extended_text.strip())
            
            # Также можем использовать passages как дополнительный текст
            if "extended-text" not in result_item or not result_item["extended-text"]:
                passages = doc.find("passages")
                if passages is not None:
                    passage_texts = []
                    for passage in passages.findall("passage"):
                        if passage.text:
                            passage_texts.append(passage.text.strip())
                        else:
                            passage_text = "".join(passage.itertext())
                            if passage_text:
                                passage_texts.append(passage_text.strip())
                    
                    if passage_texts:
                        result_item["extended-text"] = remove_html_tags(" ".join(passage_texts))
            
            # Если нашли хотя бы одно поле, добавляем результат
            if result_item:
                results.append(result_item)
        
        # Если не нашли через ElementTree, пытаемся через BeautifulSoup
        if not results:
            soup = BeautifulSoup(xml_content, 'xml')
            
            for doc in soup.find_all('doc'):
                result_item = {}
                
                # Ищем headline
                headline = doc.find('headline')
                if headline:
                    headline_text = headline.get_text(strip=True)
                    if headline_text:
                        result_item["headline"] = remove_html_tags(headline_text)
                
                # Ищем extended-text внутри properties
                properties = doc.find('properties')
                if properties:
                    extended_text_elem = properties.find('extended-text')
                    if extended_text_elem:
                        extended_text = extended_text_elem.get_text(strip=True)
                        if extended_text:
                            result_item["extended-text"] = remove_html_tags(extended_text)
                
                # Если нет extended-text, используем passages
                if "extended-text" not in result_item or not result_item.get("extended-text"):
                    passages = doc.find('passages')
                    if passages:
                        passage_texts = []
                        for passage in passages.find_all('passage'):
                            passage_text = passage.get_text(strip=True)
                            if passage_text:
                                passage_texts.append(passage_text)
                        if passage_texts:
                            result_item["extended-text"] = remove_html_tags(" ".join(passage_texts))
                
                if result_item:
                    results.append(result_item)
    
    except ET.ParseError as e:
        # Если XML невалидный, пытаемся парсить как HTML через BeautifulSoup
        try:
            print(f"Ошибка парсинга XML через ElementTree: {e}, пробуем BeautifulSoup...")
            soup = BeautifulSoup(xml_content, 'html.parser')
            
            for doc in soup.find_all(['doc', 'document']):
                result_item = {}
                
                headline = doc.find('headline')
                if headline:
                    headline_text = headline.get_text(strip=True)
                    if headline_text:
                        result_item["headline"] = remove_html_tags(headline_text)
                
                properties = doc.find('properties')
                if properties:
                    extended_text_elem = properties.find('extended-text')
                    if extended_text_elem:
                        extended_text = extended_text_elem.get_text(strip=True)
                        if extended_text:
                            result_item["extended-text"] = remove_html_tags(extended_text)
                
                if result_item:
                    results.append(result_item)
        except Exception as e2:
            print(f"Ошибка при парсинге результатов: {e2}")
    
    except Exception as e:
        print(f"Ошибка при парсинге XML: {e}")
    
    return results


def remove_html_tags(text: str) -> str:
    """
    Удаляет все HTML/XML теги из текста.
    
    Args:
        text: Текст с тегами
        
    Returns:
        Текст без тегов
    """
    if not text:
        return ""
    
    # Используем BeautifulSoup для удаления тегов
    soup = BeautifulSoup(text, 'html.parser')
    clean_text = soup.get_text()
    
    # Убираем лишние пробелы и переносы строк
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text


def get_generative_answer(user_query: str) -> str:
    """
    Получает генеративный ответ от Яндекса.
    
    Args:
        user_query: Запрос пользователя
        
    Returns:
        Генеративный ответ от Яндекса
    """
    url = "https://searchapi.api.cloud.yandex.net/v2/gen/search"
    
    payload = {
        "messages": [
            {
                "content": user_query,
                "role": "ROLE_USER"
            }
        ],
        "searchType": "SEARCH_TYPE_RU",
        "folderId": get_yandex_folder_id(),
        "fixMisspell": True,
        "getPartialResults": False
    }
    
    headers = {
        "Authorization": get_yandex_auth_token(),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # Извлекаем генеративный ответ из JSON
        # Структура ответа может отличаться, поэтому проверяем несколько вариантов
        if "alternative" in result and len(result["alternative"]) > 0:
            message = result["alternative"][0].get("message", {})
            return message.get("text", "")
        elif "response" in result:
            return result["response"]
        elif "text" in result:
            return result["text"]
        else:
            return json.dumps(result, ensure_ascii=False)
    
    except Exception as e:
        print(f"Ошибка при получении генеративного ответа: {e}")
        return ""


def preprocess_text(text: str) -> str:
    """
    Предобрабатывает текст: символы \n меняем на /n, enter меняем на \n.
    
    Args:
        text: Исходный текст
        
    Returns:
        Предобработанный текст
    """
    if not text:
        return ""
    
    # Заменяем символы \n (обратный слэш + n) на /n
    text = text.replace("\\n", "/n")
    
    # Заменяем реальные переносы строк на \n
    text = text.replace("\n", "\\n").replace("\r\n", "\\n").replace("\r", "\\n")
    
    return text


def get_final_answer_from_llm(user_query: str, context: str) -> str:
    """
    Получает финальный ответ от Ollama на основе контекста.
    
    Args:
        user_query: Исходный запрос пользователя
        context: Собранный контекст (предобработанные запросы + генеративный ответ)
        
    Returns:
        Финальный ответ от LLM
    """
    prompt = PROMPT_FINAL_ANSWER.format(
        user_query=user_query,
        context=context
    )
    
    payload = {
        "model": ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_ctx": 16384}
    }
    
    try:
        response = requests.post(get_ollama_url(), json=payload)
        response.raise_for_status()
        result = response.json()
        
        return result.get("response", "").strip()
    except Exception as e:
        print(f"Ошибка при получении финального ответа: {e}")
        return ""


def format_search_results(results: List[Dict[str, str]]) -> str:
    """
    Форматирует результаты поиска для контекста.
    
    Args:
        results: Список результатов поиска
        
    Returns:
        Отформатированная строка с результатами
    """
    formatted_results = []
    
    for idx, result in enumerate(results, 1):
        parts = []
        
        if "headline" in result and result["headline"]:
            parts.append(f"[{idx}] {result['headline']}")
        
        if "extended-text" in result and result["extended-text"]:
            parts.append(result["extended-text"])
        
        if parts:
            formatted_results.append(" ".join(parts))
    
    return "\n".join(formatted_results)


async def get_yandex_search_results(user_query: str) -> tuple[str, str]:
    """
    Получает результаты поиска из Yandex без финальной обработки через LLM.
    Возвращает отформатированные результаты поиска и генеративный ответ.
    
    Args:
        user_query: Исходный запрос пользователя
        
    Returns:
        Кортеж (formatted_results, generative_answer) - отформатированные результаты поиска и генеративный ответ
    """
    logger = logging.getLogger(__name__)
    
    logger.info("Генерация поисковых запросов для Yandex...")
    search_queries = await asyncio.to_thread(generate_search_queries, user_query)
    logger.info(f"Сгенерировано запросов: {len(search_queries)}")
    
    logger.info("Выполнение поиска для каждого запроса...")
    all_search_results = []
    for query in search_queries:
        logger.info(f"  Поиск: {query}")
        xml_response = await asyncio.to_thread(search_yandex, query)
        if xml_response:
            results = parse_search_results(xml_response)
            all_search_results.extend(results)
            logger.info(f"    Найдено результатов: {len(results)}")
    
    logger.info(f"Всего собрано результатов: {len(all_search_results)}")
    
    formatted_results = format_search_results(all_search_results)
    
    logger.info("Получение генеративного ответа от Яндекса...")
    generative_answer = await asyncio.to_thread(get_generative_answer, user_query)
    logger.info(f"Генеративный ответ получен: {len(generative_answer)} символов")
    
    return formatted_results, generative_answer


async def main(user_query: str) -> str:
    """
    Главная функция, которая последовательно выполняет все шаги.
    Асинхронная версия для использования в async контексте.
    
    Args:
        user_query: Исходный запрос пользователя
        
    Returns:
        Финальный ответ с пояснением
    """
    logger = logging.getLogger(__name__)
    
    logger.info("Шаг 1: Генерация поисковых запросов...")
    # Выполняем синхронные вызовы в отдельном потоке
    search_queries = await asyncio.to_thread(generate_search_queries, user_query)
    logger.info(f"Сгенерировано запросов: {len(search_queries)}")
    for q in search_queries:
        logger.info(f"  - {q}")
    
    logger.info("\nШаг 2: Выполнение поиска для каждого запроса...")
    all_search_results = []
    for query in search_queries:
        logger.info(f"  Поиск: {query}")
        xml_response = await asyncio.to_thread(search_yandex, query)
        if xml_response:
            results = parse_search_results(xml_response)
            all_search_results.extend(results)
            logger.info(f"    Найдено результатов: {len(results)}")
    
    logger.info(f"\nВсего собрано результатов: {len(all_search_results)}")
    
    logger.info("\nШаг 3: Парсинг результатов...")
    formatted_results = format_search_results(all_search_results)
    
    logger.info("\nШаг 4: Получение генеративного ответа от Яндекса...")
    generative_answer = await asyncio.to_thread(get_generative_answer, user_query)
    logger.info(f"Генеративный ответ получен: {len(generative_answer)} символов")
    
    logger.info("\nШаг 5: Предобработка текста и сборка контекста...")
    # Предобрабатываем результаты поиска
    preprocessed_results = preprocess_text(formatted_results)
    
    # Предобрабатываем генеративный ответ
    preprocessed_generative = preprocess_text(generative_answer)
    
    # Собираем контекст
    context_parts = []
    if preprocessed_results:
        context_parts.append(f"РЕЗУЛЬТАТЫ ПОИСКА:\n{preprocessed_results}")
    if preprocessed_generative:
        context_parts.append(f"\nГЕНЕРАТИВНЫЙ ОТВЕТ ОТ ЯНДЕКСА:\n{preprocessed_generative}")
    
    context = "\n".join(context_parts)
    
    logger.info("\nШаг 6: Получение финального ответа от LLM...")
    final_answer = await asyncio.to_thread(get_final_answer_from_llm, user_query, context)
    
    # Формируем финальный ответ с пояснением
    response = (
        "⚠️ В базе знаний (vault) не найдено информации по вашему запросу.\n"
        "Однако, вот что удалось найти в интернете:\n\n"
        f"{final_answer}"
    )
    
    return response


if __name__ == "__main__":
    if content:
        result = main(content)
        print("\n" + "="*80)
        print("ФИНАЛЬНЫЙ ОТВЕТ:")
        print("="*80)
        print(result)

