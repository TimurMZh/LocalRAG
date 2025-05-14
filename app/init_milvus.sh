#!/bin/bash

# Скрипт для инициализации коллекций Milvus

# Переходим в директорию скрипта
cd "$(dirname "$0")"

# Проверяем наличие аргумента --force
FORCE=""
if [ "$1" == "--force" ]; then
    FORCE="--force"
    echo "Режим пересоздания коллекций активирован"
fi

# Устанавливаем переменную PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Запускаем скрипт инициализации
echo "Запуск инициализации коллекций Milvus..."
python utils/init_mivus_collection.py $FORCE

# Проверяем результат выполнения
if [ $? -eq 0 ]; then
    echo "Инициализация коллекций Milvus успешно завершена"
else
    echo "Ошибка при инициализации коллекций Milvus"
    exit 1
fi 