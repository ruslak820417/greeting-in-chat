# Финальный отчёт: Claude Code Agent Teams

> Подготовлено командой агентов | 2026-03-13

---

## 1. Резюме исследования

Исследование проведено web-researcher, охватывает 15 тезисов из 12 источников.

**Ключевые находки:**

- **Agent Teams** — экспериментальная функция Claude Code, позволяющая координировать несколько независимых экземпляров Claude Code, работающих параллельно с межагентной коммуникацией. Требует `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` и Claude Code v2.1.32+.

- **Архитектура** состоит из четырёх компонентов: Team Lead (главная сессия), Teammates (отдельные Claude Code instances), Task List (общий список задач с зависимостями), Mailbox (система обмена сообщениями через SendMessage).

- **Принципиальное отличие от Subagents:** subagents только отчитываются основному агенту; в Agent Teams teammates общаются напрямую, делят task list и координируются самостоятельно.

- **Два режима отображения:** in-process (один терминал, Shift+Down) и split panes (tmux/iTerm2, каждый teammate в своей панели).

- **Task management:** три состояния (pending, in_progress, completed), dependency tracking с автоматической разблокировкой, file locking для предотвращения race conditions.

- **Контекст:** teammates загружают проектный контекст (CLAUDE.md, MCP серверы, skills), но НЕ наследуют conversation history от lead. Контекст передаётся через spawn prompt.

- **Оптимальный размер команды:** 3–5 teammates, 5–6 задач на каждого. Стоимость: ~3–4x токенов одной сессии.

- **Экономия:** можно назначать разные модели (Opus для reasoning, Sonnet для implementation), экономя 40–60% на токенах.

- **Quality gates:** хуки TeammateIdle и TaskCompleted для автоматического feedback.

- **Лучшие use cases:** research & review, новые модули, debugging с конкурирующими гипотезами, cross-layer координация.

- **Ограничения:** нет session resumption для in-process teammates, одна команда на сессию, нет вложенных команд, split panes только tmux/iTerm2, lead фиксирован.

---

## 2. Проверенные тезисы

Верификация проведена fact-checker на основе официальной документации Anthropic.

| # | Тезис | Статус | Доверие |
|---|-------|--------|---------|
| 1 | Agent Teams — экспериментальная функция, требует `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` | ✅ approved | high |
| 2 | Split-pane режим через tmux или iTerm2 | ✅ approved | high |
| 3 | Lead + teammates как отдельные Claude Code сессии | ✅ approved | high |
| 4 | Прямая коммуникация через SendMessage | ✅ approved | high |
| 5 | Параллельное выполнение задач несколькими агентами | ✅ approved | high |

**Все 5 ключевых тезисов подтверждены с высоким уровнем доверия.**

### Дополнительные верифицированные факты

- Требуется Claude Code v2.1.32+
- `teammateMode` управляет режимом: `"auto"` (по умолчанию), `"tmux"`, `"iterm2"`
- Split panes не поддерживаются в VS Code terminal, Windows Terminal, Ghostty
- Broadcast стоит дорого — cost scales с размером команды
- Team config хранится в `~/.claude/teams/{team-name}/config.json`
- Tasks хранятся в `~/.claude/tasks/{team-name}/`

### Известные баги (GitHub Issues)

- #24292 — teammateMode "tmux" может не триггерить iTerm2 split panes
- #23615 — agent teams spawn в новом tmux window вместо split pane
- #24771 — split panes открываются, но teammates disconnected от messaging
- #24385 — iTerm2 panes не закрываются при shutdown

### Риски для демо

- Split pane mode имеет известные баги — может потребоваться fallback на in-process
- Cleanup должен запускаться только через lead
- При resumption in-process teammates не восстанавливаются

---

## 3. YouTube Script Outline

Структура видео (~9–10 минут), подготовлена script-architect:

| Таймкод | Секция | Содержание |
|---|---|---|
| 0:00–0:30 | HOOK | Провокационное утверждение + тизер tmux с 6 агентами |
| 0:30–1:30 | ПОЧЕМУ СЕЙЧАС | Переход от single-agent к multi-agent, Anthropic первый |
| 1:30–3:30 | ЧТО ТАКОЕ | Архитектура, 4 компонента, отличие от subagents, аналогия с фрилансерами |
| 3:30–6:30 | КАК РАБОТАЕТ | Настройка → Запуск → Параллельная работа → Зависимости и handoff |
| 6:30–8:30 | PROOF | Демонстрация артефактов, side-by-side до/после |
| 8:30–9:30 | ИТОГ + CTA | Shift к AI-командам, потенциал, вопрос зрителям |

Выбранный hook: **Hook C** — "Anthropic только что выпустил фичу, которую я не ожидал увидеть ещё минимум год."

---

## 4. Полный скрипт

Полный текст скрипта с закадровым текстом, визуальными метками и техническими пометками для монтажа доступен в:

📄 **[agent-runtime/outputs/video-script.md](./video-script.md)**

---

## 5. Источники

### Первичные (официальные)
1. https://code.claude.com/docs/en/agent-teams — Официальная документация Agent Teams
2. https://code.claude.com/docs/en/costs — Стоимость и токены
3. https://code.claude.com/docs/en/sub-agents — Subagents (для сравнения)
4. https://www.anthropic.com/engineering/building-c-compiler — Case study: C compiler with agent teams

### Вторичные (сообщество)
5. https://medium.com/@dan.avila7/agent-teams-in-claude-code-d6bb90b3333b — Daniel Avila, Medium
6. https://cobusgreyling.medium.com/claude-code-agent-teams-ca3ec5f2d26a — Cobus Greyling, Medium
7. https://addyosmani.com/blog/claude-code-agent-teams/ — Addy Osmani, Claude Code Swarms
8. https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/ — alexop.dev
9. https://paddo.dev/blog/claude-code-hidden-swarm/ — Hidden Multi-Agent System
10. https://www.turingcollege.com/blog/claude-agent-teams-explained — Turing College Guide
11. https://www.sitepoint.com/anthropic-claude-code-agent-teams/ — SitePoint Guide
12. https://claudefa.st/blog/guide/agents/agent-teams — Claudefast Guide
13. https://cuttlesoft.com/blog/2026/02/24/setting-up-claude-code-agent-teams-on-macos/ — macOS Setup Guide

### GitHub Issues
14. https://github.com/anthropics/claude-code/issues/23615 — tmux UX
15. https://x.com/EricBuess/status/2028217923760959976 — Eric Buess (tmux cleanup)

---

*Статус: ✅ Отчёт собран. Готов к экспорту в PDF.*
