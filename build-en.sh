#!/bin/bash
# Генерирует en.html из index.html: английские метатеги и английский язык по умолчанию.
# Запускать после каждой правки index.html, затем коммитить оба файла.
cd "$(dirname "$0")" && python3 build-en.py && echo "en.html пересобран"
