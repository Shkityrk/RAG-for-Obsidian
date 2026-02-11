from langchain.text_splitter import CharacterTextSplitter


class CustomTextSplitter:
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 128) -> None:
        # Уменьшенный размер чанка для совместимости с моделями embeddings
        self.chunk_size = chunk_size
        self.splitter_level1 = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator=r"[#]+ ",
            is_separator_regex=True,
            )
        self.splitter_level2 = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator="\n\n",
            is_separator_regex=False,
            )
        self.splitter_level3 = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separator="\n",
            is_separator_regex=False,
            )

    def split(self, text: str) -> list[str]:
        chunks = self.splitter_level1.split_text(text)
        results = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size:
                results.extend(self.splitter_level2.split_text(chunk))
            else:
                results.append(chunk)
        chunks = results
        results = []
        for chunk in chunks:
            if len(chunk) > self.chunk_size:
                results.extend(self.splitter_level3.split_text(chunk))
            else:
                results.append(chunk)
        
        # Финальная проверка: если какой-то чанк все еще слишком большой, принудительно разбиваем
        final_results = []
        max_safe_size = 256  # Максимальный безопасный размер для embeddings
        for chunk in results:
            if len(chunk) > max_safe_size:
                # Принудительное разбиение на части по max_safe_size
                for i in range(0, len(chunk), max_safe_size):
                    final_results.append(chunk[i:i + max_safe_size])
            else:
                final_results.append(chunk)
        
        return final_results
