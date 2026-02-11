from datetime import datetime

from pydantic import BaseModel, Field


class FragmentInfoSchema(BaseModel):
    """Информация о фрагменте текста из документа"""
    filename: str = Field(examples=["C++.md"])
    text: str = Field(examples=["C++ is a powerful programming language..."])
    similarity: float = Field(examples=[0.85])
    chunk_id: int | None = Field(default=None, examples=[123])


class MessageSchema(BaseModel):
    id: int = Field(examples=[1])
    role: str = Field(examples=["user"])
    content: str = Field(examples=["Какой язык стоит учить после Python?"])
    created_date: datetime
    fragments: list[FragmentInfoSchema] = Field(default_factory=list, description="Фрагменты текста, использованные для генерации ответа")


class MessageHistoryResponse(BaseModel):
    messages: list[MessageSchema]


class QueryRequest(BaseModel):
    content: str = Field(examples=["Какой язык стоит учить после Python?"])
    chat_id: int = Field(examples=[1], description="ID чата для сохранения сообщений")
    vault_id: int = Field(examples=[1], description="ID волта для поиска в контексте")


class AnswerResponse(BaseModel):
    answer: str = Field(examples=["Конечно же C++"])
    related_documents: list[str] = Field(examples=[["C++.md", "Python vs C++.md"]])
    fragments: list[FragmentInfoSchema] = Field(default_factory=list, description="Фрагменты текста, использованные для генерации ответа")
    message_id: int = Field(description="ID созданного сообщения в БД")
