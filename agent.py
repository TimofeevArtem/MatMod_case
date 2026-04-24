import json
import os
from groq import Groq
from typing import Optional
from dotenv import load_dotenv
from config import config
from tools.api_tool import get_historical_information, get_currency_rate, show_graph
from groq import Groq, RateLimitError, BadRequestError, PermissionDeniedError 

load_dotenv()

llm_config = config["llm"]
groq_model = Groq(api_key=os.getenv("GROQ_API_KEY"))

system_prompt = config["agent"]["system_prompt"]
    
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_currency_rate",
            "description": "Получает текущий курс валюты по данным Центрального Банка России.",
            "parameters": {
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "Трёхбуквенный код валюты (например, USD, EUR, GBP).",
                    },
                    "date": {
                        "type": "string",
                        "description": "Дата, на которую нужно получить курс (формат: DD.MM.YYYY).",
                    },
                },
                "required": ["currency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_information",
            "description": "Получает данные о курсах валюты за указанный период.",
            "parameters": {
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "Трёхбуквенный код валюты (например, USD, EUR, GBP).",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Начальная дата периода (формат: DD.MM.YYYY).",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Конечная дата периода (формат: DD.MM.YYYY).",
                    },
                },
                "required": ["currency", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_graph",
            "description": "Создаёт график курса валюты.",
            "parameters": {
                "type": "object",
                "properties": {
                    "currency": {
                        "type": "string",
                        "description": "Трёхбуквенный код валюты (например, USD, EUR, GBP).",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Начальная дата периода (формат: DD.MM.YYYY).",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Конечная дата периода (формат: DD.MM.YYYY).",
                    },
                },
                "required": ["currency", "start_date", "end_date"],
            },
        },
    }
]

available_functions = {
    "get_currency_rate": get_currency_rate,
    "get_historical_information": get_historical_information,
    "show_graph": show_graph
}

def run_agent(user_message: str, chat_history: Optional[list] = None):
    """Основная функция для общения с агентом."""
    try:
        if chat_history is None:
            chat_history = [
                {"role": "system", "content": system_prompt}
            ]
        chat_history.append({"role": "user", "content": user_message})

        response = groq_model.chat.completions.create(
            model=llm_config["model_id"],
            messages=chat_history,
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message

        while response_message.tool_calls:
            chat_history.append(response_message)
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                if function_name in available_functions:
                    result = available_functions[function_name](**function_args)
                else:
                    result = {f"Неизвестная функция: {function_name}"}
                chat_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })
            response = groq_model.chat.completions.create(
                model=llm_config["model_id"],
                messages=chat_history,
                temperature=llm_config["temperature"],
                max_tokens=llm_config["max_tokens"],
                tools=tools,
                tool_choice="auto",
            )
            
            response_message = response.choices[0].message

        chat_history.append(response_message)
        return response_message.content, chat_history
        
    except RateLimitError as e:
        error_msg = "Превышен лимит запросов."
        print(f"Ошибка: {e}")
        return error_msg, chat_history
    except BadRequestError as e:
        error_msg = f"Ошибка в запросе: {str(e)}"
        print(f"Ошибка: {e}")
        return error_msg, chat_history
    except PermissionDeniedError as e:
        error_msg = "Ошибка доступа."
        print(f"Ошибка: {e}")
        return error_msg, chat_history
    except Exception as e:
        error_msg = f"Ошибка: {str(e)}"
        print(f"Ошибка: {e}")
        return error_msg, chat_history


chat_history = None

print("Валютный ассистент (для выхода напиши 'выход')")

while True:
    user_input = input("\nВы: ")
    
    if user_input.lower() in ["выход", "exit", "quit"]:
        print("До свидания!")
        break
    
    answer, chat_history = run_agent(user_input, chat_history)
    print(f"\nАссистент: {answer}")