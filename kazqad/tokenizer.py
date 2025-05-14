import re
import unicodedata
from typing import List, Dict, Any, Optional


class KazakhTokenizer:
    KAZAKH_STOPWORDS = {
        'бұл', 'сол', 'мен', 'сен', 'ол', 'біз', 'сіз',
        'және', 'өте', 'тек', 'содан', 'сонда'
    }

    KAZAKH_SUFFIXES = [
        'лар', 'лер', 'дар', 'дер',
        'тар', 'тер', 'шыл', 'шіл',
        'мен', 'бен', 'пен',
        'да', 'де', 'та', 'те'
    ]

    STEMMING_EXCEPTIONS = [
        'әріптер', 'нүктелер', 'үтірлер',
        'тілінде', 'кітаптар', 'адамдар'
    ]

    @classmethod
    def normalize_text(cls, text: str) -> str:
        """
        Нормализация текста с учетом особенностей казахского языка
        """
        # Привести к нижнему регистру
        text = text.lower()

        # Удаление диакритических знаков
        text = ''.join(
            char for char in unicodedata.normalize('NFKD', text)
            if unicodedata.category(char) != 'Mn'
        )

        return text

    @classmethod
    def tokenize(
            cls,
            text: str,
            remove_stopwords: bool = False,
            apply_stemming: bool = False
    ) -> List[str]:
        """
        Токенизация с расширенной обработкой казахских символов
        """
        # Нормализация
        text = cls.normalize_text(text)

        # Очистка от пунктуации и специальных символов
        text = re.sub(
            r'[^\w\sәіңғүұқөһ\-]',
            ' ',
            text
        )

        # Токенизация
        tokens = text.split()

        # Удаление стоп-слов
        if remove_stopwords:
            tokens = [
                token for token in tokens
                if token not in cls.KAZAKH_STOPWORDS
            ]

        # Стемминг
        if apply_stemming:
            tokens = [
                cls._stem_token(token) for token in tokens
            ]

        return tokens

    @classmethod
    def _stem_token(cls, token: str) -> str:
        """
        Стемминг токена с учетом особенностей казахского языка
        """
        # Пропуск исключений
        if token in cls.STEMMING_EXCEPTIONS:
            return token

        # Удаление суффиксов
        for suffix in cls.KAZAKH_SUFFIXES:
            if (token.endswith(suffix) and
                    len(token) > len(suffix) + 2):
                token = token[:-len(suffix)]
                break

        return token

    @classmethod
    def get_token_metrics(cls, tokens: List[str]) -> Dict[str, Any]:
        """
        Получение метрик для набора токенов
        """
        return {
            'total_tokens': len(tokens),
            'unique_tokens': len(set(tokens)),
            'avg_token_length': sum(len(t) for t in tokens) / len(tokens) if tokens else 0,
            'kazakh_char_tokens': sum(
                1 for token in tokens
                if any(char in 'әіңғүұқөһ' for char in token)
            )
        }