from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware import before_model
from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime


@before_model
def trim_messages_middleware(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """
    Middleware для безопасной обрезки истории сообщений.
    Оставляет системный промпт (или самое первое сообщение) и несколько последних.
    
    Для чего это нужно:
    Контекстное окно LLM ограничено. Если диалог становится слишком длинным, 
    мы превысим лимит токенов (TokenLimitExceeded) и получим ошибку API, 
    либо модель начнет "галлюцинировать", забывая начало, и мы будем платить 
    за лишние переданные токены.
    """
    messages = state["messages"]

    # Если история короткая, ничего не трогаем — экономим процессорное время
    if len(messages) <= 3:
        return None  

    # 1. Запоминаем первое сообщение (обычно это SystemMessage с инструкциями агента)
    first_msg = messages[0]
    
    # 2. Высчитываем последние сообщения. 
    # Важно: берем четное количество, чтобы не разорвать пару HumanMessage/AIMessage
    # Если мы оставим ответ AI без вопроса человека, модель может запутаться.
    if len(messages) % 2 == 0:
        recent_messages = messages[-3:]
    else:
        recent_messages = messages[-4:]
        
    # Формируем новый список сообщений
    new_messages = [first_msg] + recent_messages

    # 3. Возвращаем специальную команду для обновления состояния.
    # Мы используем RemoveMessage(id=REMOVE_ALL_MESSAGES), потому что LangGraph 
    # по умолчанию добавляет новые сообщения к старым (append-only reducer). 
    # Если просто вернуть новые сообщения, они продублируются в конце истории.
    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }
