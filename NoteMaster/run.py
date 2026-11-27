#!/usr/bin/env python
"""Точка входа NoteMaster Core v1.0.

Запуск:
    python run.py                  # интерактивный режим
    python run.py --data-dir mydata
    python run.py --check          # проверка целостности
    python run.py --debug          # режим отладки
"""

from __future__ import annotations

import sys

from app.main import main
from app.utils.helpers import configure_console_output

configure_console_output()
sys.exit(main())
