# Research Summary: Claude Code Agent Teams

**Дата:** 2026-03-13
**Автор:** web-researcher
**Статус:** Готово к проверке fact-checker

---

### Тезис 1
**Утверждение:** Agent Teams — экспериментальная функция Claude Code, позволяющая координировать несколько независимых экземпляров Claude Code, работающих параллельно над общим проектом с межагентной коммуникацией.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Это фундаментальное определение темы, ключевое для YouTube-видео. Зритель должен сразу понять что это и зачем.

### Тезис 2
**Утверждение:** Для включения Agent Teams необходимо установить переменную окружения `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` в settings.json или shell. Требуется Claude Code v2.1.32+.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Обязательное техническое требование. Без этого флага функция недоступна.

### Тезис 3
**Утверждение:** Архитектура Agent Teams состоит из четырёх компонентов: Team Lead (главная сессия), Teammates (независимые экземпляры Claude Code), Task List (общий список задач с зависимостями), Mailbox (система обмена сообщениями).
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Ключевая архитектурная схема — основа для визуализации в видео.

### Тезис 4
**Утверждение:** Принципиальное отличие Agent Teams от Subagents: subagents только отчитываются основному агенту и не общаются друг с другом; в Agent Teams teammates общаются напрямую, делят task list и координируются самостоятельно.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Критическое различие для объяснения зрителям — почему Agent Teams это шаг вперёд.

### Тезис 5
**Утверждение:** Agent Teams поддерживают два режима отображения: in-process (все в одном терминале, Shift+Down для переключения) и split panes (каждый teammate в своей панели, требует tmux или iTerm2).
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Split panes через tmux — визуально самый эффектный вариант для демо. Важно для YouTube.

### Тезис 6
**Утверждение:** Задачи в Agent Teams имеют три состояния (pending, in_progress, completed), поддерживают dependency tracking с автоматической разблокировкой, и используют file locking для предотвращения race conditions при одновременном claim.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Демонстрация dependency tracking — яркий момент для видео, показывающий "умность" системы.

### Тезис 7
**Утверждение:** Teammates при запуске загружают проектный контекст (CLAUDE.md, MCP серверы, skills), но НЕ наследуют conversation history от lead. Важный контекст передаётся через spawn prompt.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Объясняет почему spawn prompt должен быть подробным и как agents делят контекст.

### Тезис 8
**Утверждение:** Agent Teams появились вместе с релизом Opus 4.6 как экспериментальная функция Anthropic.
**Источник:** https://medium.com/@dan.avila7/agent-teams-in-claude-code-d6bb90b3333b
**Почему важно:** Исторический контекст — когда и с чем появилась функция.

### Тезис 9
**Утверждение:** Оптимальный размер команды 3-5 teammates с 5-6 задачами на каждого. Стоимость в токенах: 3-teammate team ≈ 3-4x токенов одной сессии.
**Источник:** https://code.claude.com/docs/en/agent-teams, https://code.claude.com/docs/en/costs
**Почему важно:** Практический совет для зрителей + прозрачность по стоимости.

### Тезис 10
**Утверждение:** Можно назначать разные модели разным teammates (Opus для reasoning, Sonnet для implementation), экономя 40-60% на токенах.
**Источник:** https://code.claude.com/docs/en/costs
**Почему важно:** Лайфхак для оптимизации расходов — ценный практический совет.

### Тезис 11
**Утверждение:** Lead может требовать Plan Approval от teammates: teammate работает в read-only plan mode, lead одобряет или отклоняет план с feedback перед implementation.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Показывает уровень контроля и safety — важный аргумент для enterprise.

### Тезис 12
**Утверждение:** Среди ограничений: нет session resumption для in-process teammates, одна команда на сессию, нет вложенных команд, split panes только tmux/iTerm2, lead фиксирован.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Честное освещение ограничений повышает доверие зрителей.

### Тезис 13
**Утверждение:** Лучшие use cases для Agent Teams: research & review, новые модули/фичи, debugging с конкурирующими гипотезами, cross-layer координация (frontend + backend + tests).
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Чёткие сценарии применения помогают зрителю понять когда это использовать.

### Тезис 14
**Утверждение:** Quality gates через хуки: TeammateIdle (когда teammate собирается idle) и TaskCompleted (при завершении задачи) позволяют автоматически возвращать feedback и предотвращать некачественное завершение.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Механизм контроля качества на уровне системы — продвинутая возможность.

### Тезис 15
**Утверждение:** Cleanup команды должен выполняться только через lead-сессию. Если teammates ещё активны, cleanup завершится ошибкой. Сначала shutdown teammates, потом cleanup.
**Источник:** https://code.claude.com/docs/en/agent-teams
**Почему важно:** Важная практическая инструкция для корректного завершения демо.

---

## Все использованные источники

1. https://code.claude.com/docs/en/agent-teams — Официальная документация (основной)
2. https://code.claude.com/docs/en/costs — Стоимость и токены
3. https://code.claude.com/docs/en/sub-agents — Subagents (для сравнения)
4. https://medium.com/@dan.avila7/agent-teams-in-claude-code-d6bb90b3333b — Daniel Avila, Medium
5. https://cobusgreyling.medium.com/claude-code-agent-teams-ca3ec5f2d26a — Cobus Greyling, Medium
6. https://addyosmani.com/blog/claude-code-agent-teams/ — Addy Osmani, Claude Code Swarms
7. https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/ — alexop.dev
8. https://paddo.dev/blog/claude-code-hidden-swarm/ — Hidden Multi-Agent System
9. https://www.turingcollege.com/blog/claude-agent-teams-explained — Turing College Guide
10. https://www.sitepoint.com/anthropic-claude-code-agent-teams/ — SitePoint Guide
11. https://github.com/anthropics/claude-code/issues/23615 — GitHub Issue (tmux UX)
12. https://x.com/EricBuess/status/2028217923760959976 — Eric Buess (tmux cleanup)
