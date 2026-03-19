# Verified Claims — Agent Teams Fact-Check

**Дата проверки:** 2026-03-13
**Проверил:** fact-checker
**Основной источник:** https://code.claude.com/docs/en/agent-teams (официальная документация Anthropic)

---

### Тезис 1
**Утверждение:** Agent Teams — экспериментальная функция Claude Code, требует `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено дословно в официальной документации: "Agent teams are experimental and disabled by default. Enable them by adding CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS to your settings.json or environment." Значение переменной `1` корректно. Требуется Claude Code v2.1.32 или новее.

---

### Тезис 2
**Утверждение:** Agent Teams используют tmux или iTerm2 для split-pane режима
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено. Документация описывает два display mode: "In-process" (все в одном терминале) и "Split panes" (каждый teammate в своём pane). Split panes требуют tmux или iTerm2 с `it2` CLI. Параметр `teammateMode` в settings.json управляет режимом. По умолчанию — `"auto"` (split panes если уже в tmux, иначе in-process). Рекомендуется `tmux -CC` в iTerm2. Ограничение: split panes не поддерживаются в VS Code integrated terminal, Windows Terminal и Ghostty.

---

### Тезис 3
**Утверждение:** В Agent Teams есть lead-агент и teammates, которые работают как отдельные Claude Code сессии
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено точно. Архитектура: Team lead (основная сессия, создаёт команду, координирует), Teammates (отдельные Claude Code instances со своим context window), Task list (общий список задач), Mailbox (система обмена сообщениями). Каждый teammate загружает тот же проектный контекст (CLAUDE.md, MCP servers, skills), но НЕ наследует conversation history lead-а. Lead фиксирован на весь lifetime команды. Teammates не могут создавать свои команды (no nested teams).

---

### Тезис 4
**Утверждение:** Teammates могут общаться напрямую через SendMessage
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено. Документация явно указывает: "Teammates message each other directly." Два типа коммуникации: `message` (отправка конкретному teammate) и `broadcast` (отправка всем, используется экономно — cost scales with team size). Сообщения доставляются автоматически, lead не нужно poll. Также есть idle notifications — teammate уведомляет lead при завершении. Ключевое отличие от subagents: subagents "report results back to the main agent only", а teammates общаются друг с другом.

---

### Тезис 5
**Утверждение:** Agent Teams поддерживают параллельное выполнение задач несколькими агентами
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено. Это ключевая фича Agent Teams. Документация: "Agent teams are most effective for tasks where parallel exploration adds real value." Примеры: research and review (параллельное исследование), new modules (каждый teammate владеет частью), debugging (конкурирующие гипотезы), cross-layer coordination. Token cost ~3-4x от single session, но выигрыш по времени оправдывает. Рекомендуемый размер команды: 3-5 teammates, 5-6 tasks per teammate. Task claiming использует file locking для предотвращения race conditions.

---

---

## Фаза 2 — Проверка тезисов 6-15 из research-summary.md

### Тезис 6
**Утверждение:** Задачи в Agent Teams имеют три состояния (pending, in_progress, completed), поддерживают dependency tracking с автоматической разблокировкой, и используют file locking для предотвращения race conditions.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено. Официальная документация: "Tasks have three states: pending, in progress, and completed. Tasks can also depend on other tasks: a pending task with unresolved dependencies cannot be claimed until those dependencies are completed." И: "Task claiming uses file locking to prevent race conditions when multiple teammates try to claim the same task simultaneously."

---

### Тезис 7
**Утверждение:** Teammates при запуске загружают проектный контекст (CLAUDE.md, MCP серверы, skills), но НЕ наследуют conversation history от lead.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено дословно: "When spawned, a teammate loads the same project context as a regular session: CLAUDE.md, MCP servers, and skills. It also receives the spawn prompt from the lead. The lead's conversation history does not carry over."

---

### Тезис 8
**Утверждение:** Agent Teams появились вместе с релизом Opus 4.6 как экспериментальная функция Anthropic.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://techcrunch.com/2026/02/05/anthropic-releases-opus-4-6-with-new-agent-teams/
**Примечание:** Подтверждено. TechCrunch: "Anthropic releases Opus 4.6 with new 'agent teams'" — дата публикации 5 февраля 2026. Anthropic продемонстрировала фичу: 16 параллельных агентов написали C compiler на 100,000 строк за 2 недели, прошедший 99% GCC test suite.

---

### Тезис 9
**Утверждение:** Оптимальный размер команды 3-5 teammates с 5-6 задачами на каждого. Стоимость в токенах: 3-teammate team ≈ 3-4x токенов одной сессии.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено. Документация: "Start with 3-5 teammates for most workflows" и "Having 5-6 tasks per teammate keeps everyone productive." Стоимость 3-4x подтверждена, плюс на costs page уточнение: "Agent teams use approximately 7x more tokens than standard sessions when teammates run in plan mode."

---

### Тезис 10
**Утверждение:** Можно назначать разные модели разным teammates (Opus для reasoning, Sonnet для implementation), экономя 40-60% на токенах.
**Статус:** revise
**Уровень доверия:** medium
**Источник проверки:** https://code.claude.com/docs/en/costs
**Примечание:** ЧАСТИЧНО. Документация costs page говорит: "Use Sonnet for teammates. It balances capability and cost for coordination tasks." Также: "Reserve Opus for complex architectural decisions... For simple subagent tasks, specify model: haiku." Однако цифра 40-60% экономии относится к общей стратегии model switching (Sonnet vs Opus в обычных сессиях), а НЕ конкретно к agent teams. Рекомендация для скрипта: можно упоминать экономию через model switching, но уточнять что 40-60% — это общая стратегия, а не специфичная для agent teams метрика.

---

### Тезис 11
**Утверждение:** Lead может требовать Plan Approval от teammates: teammate работает в read-only plan mode, lead одобряет или отклоняет план с feedback перед implementation.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено дословно: "For complex or risky tasks, you can require teammates to plan before implementing. The teammate works in read-only plan mode until the lead approves their approach." Lead одобряет или отклоняет с feedback. Rejected teammate stays в plan mode и пересматривает план.

---

### Тезис 12
**Утверждение:** Ограничения: нет session resumption для in-process teammates, одна команда на сессию, нет вложенных команд, split panes только tmux/iTerm2, lead фиксирован.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено полностью. Все перечисленные ограничения присутствуют в секции "Limitations" официальной документации. Дополнительно: permissions set at spawn, shutdown can be slow, task status can lag.

---

### Тезис 13
**Утверждение:** Лучшие use cases: research & review, новые модули/фичи, debugging с конкурирующими гипотезами, cross-layer координация.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено дословно. Документация перечисляет ровно эти четыре use case в секции "When to use agent teams."

---

### Тезис 14
**Утверждение:** Quality gates через хуки: TeammateIdle и TaskCompleted позволяют автоматически возвращать feedback и предотвращать некачественное завершение.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено: "TeammateIdle: runs when a teammate is about to go idle. Exit with code 2 to send feedback and keep the teammate working. TaskCompleted: runs when a task is being marked complete. Exit with code 2 to prevent completion and send feedback."

---

### Тезис 15
**Утверждение:** Cleanup команды должен выполняться только через lead-сессию. Если teammates ещё активны, cleanup завершится ошибкой.
**Статус:** approved
**Уровень доверия:** high
**Источник проверки:** https://code.claude.com/docs/en/agent-teams
**Примечание:** Подтверждено. Warning в документации: "Always use the lead to clean up. Teammates should not run cleanup because their team context may not resolve correctly, potentially leaving resources in an inconsistent state." И: "When the lead runs cleanup, it checks for active teammates and fails if any are still running."

---

## Итоговая сводка (Фаза 1 + Фаза 2)

| # | Тезис | Статус | Доверие |
|---|-------|--------|---------|
| 1 | Experimental + env var | approved | high |
| 2 | tmux / iTerm2 split panes | approved | high |
| 3 | Lead + teammates architecture | approved | high |
| 4 | SendMessage direct communication | approved | high |
| 5 | Parallel execution | approved | high |
| 6 | Task states + dependency + file locking | approved | high |
| 7 | Context loading, no history inheritance | approved | high |
| 8 | Opus 4.6 release = Agent Teams (Feb 5, 2026) | approved | high |
| 9 | 3-5 teammates, 5-6 tasks, 3-4x tokens | approved | high |
| 10 | Different models save 40-60% | **revise** | medium |
| 11 | Plan Approval mode | approved | high |
| 12 | Known limitations list | approved | high |
| 13 | Best use cases (4 categories) | approved | high |
| 14 | Quality gates (TeammateIdle, TaskCompleted) | approved | high |
| 15 | Cleanup only through lead | approved | high |

**Итого: 14 approved, 1 revise. Ни одного rejected.**

**Тезис 10 (revise):** 40-60% экономия — корректна для model switching в целом, но в скрипте нужно уточнить что это общая стратегия, а не специфичная метрика agent teams. Официальная рекомендация для agent teams: "Use Sonnet for teammates."
