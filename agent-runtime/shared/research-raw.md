# Research Raw Data: Claude Code Agent Teams

**Дата:** 2026-03-13
**Исследователь:** web-researcher agent
**Тема:** Claude Code Agent Teams — мультиагентная система в Claude Code

---

## 1. Официальная документация Anthropic

**Источник:** https://code.claude.com/docs/en/agent-teams

### Определение
Agent Teams — экспериментальная функция Claude Code, позволяющая координировать несколько экземпляров Claude Code, работающих вместе над общим проектом. Одна сессия выступает team lead, остальные — teammates.

### Включение
- Отключены по умолчанию
- Включаются через переменную окружения `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
- Можно прописать в `settings.json`:
```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```
- Требуется Claude Code v2.1.32 или выше

### Архитектура
| Компонент | Роль |
|-----------|------|
| Team lead | Главная сессия Claude Code, создаёт команду, запускает teammates, координирует работу |
| Teammates | Отдельные экземпляры Claude Code, каждый со своим контекстным окном |
| Task list | Общий список задач с зависимостями, который teammates берут и выполняют |
| Mailbox | Система обмена сообщениями между агентами |

### Режимы отображения
- **In-process** (по умолчанию): все teammates работают внутри основного терминала. Переключение через Shift+Down. Работает в любом терминале.
- **Split panes**: каждый teammate получает свою панель. Требует tmux или iTerm2.
- Режим по умолчанию `"auto"`: split panes если уже внутри tmux, иначе in-process.
- Настройка в settings.json: `"teammateMode": "tmux"` или `"in-process"`
- Флаг CLI: `claude --teammate-mode in-process`
- Split-pane НЕ поддерживается в: VS Code integrated terminal, Windows Terminal, Ghostty.

### Коммуникация
- **Автоматическая доставка сообщений**: сообщения доставляются автоматически получателям
- **Idle notifications**: когда teammate завершает работу — автоматическое уведомление lead
- **Shared task list**: все агенты видят статус задач
- **Типы сообщений**: message (одному), broadcast (всем — дорого, использовать редко)

### Задачи
- Три состояния: pending, in_progress, completed
- Задачи могут зависеть друг от друга (dependency tracking)
- Заблокированные задачи автоматически разблокируются при завершении зависимости
- File locking предотвращает race conditions при одновременном claim
- Lead может назначать задачи явно или teammates берут сами (self-claim)

### Управление
- Требование Plan Approval: teammate работает в read-only plan mode до одобрения lead
- Прямое взаимодействие с teammates через Shift+Down (in-process) или клик в pane (split)
- Shutdown: lead отправляет запрос, teammate может approve или reject
- Cleanup: только через lead, проверяет наличие активных teammates

### Хуки качества
- `TeammateIdle`: выполняется когда teammate собирается idle. Exit code 2 = отправить feedback и продолжить работу.
- `TaskCompleted`: выполняется при завершении задачи. Exit code 2 = предотвратить completion.

### Хранение
- Team config: `~/.claude/teams/{team-name}/config.json`
- Task list: `~/.claude/tasks/{team-name}/`
- Config содержит массив `members` с name, agent ID, agent type

### Permissions
- Teammates наследуют permission settings от lead
- Если lead запущен с `--dangerously-skip-permissions`, все teammates тоже
- Можно менять mode для отдельных teammates после запуска

### Контекст
- Каждый teammate загружает CLAUDE.md, MCP серверы, skills
- Получает spawn prompt от lead
- НЕ наследует conversation history от lead

### Стоимость
- Значительно больше токенов чем одна сессия
- Каждый teammate — отдельное контекстное окно
- Масштабируется линейно с количеством teammates
- 3-teammate team ≈ 3-4x токенов одной сессии, но с экономией времени

### Лучшие практики
- Давать teammates достаточно контекста в spawn prompt
- Оптимальный размер команды: 3-5 teammates
- 5-6 задач на teammate
- Начинать с research/review задач
- Избегать file conflicts (один teammate — свои файлы)
- Мониторить прогресс и корректировать

### Ограничения (limitations)
1. Нет session resumption для in-process teammates (/resume, /rewind не работают)
2. Task status может отставать (teammates забывают обновить)
3. Shutdown может быть медленным
4. Одна команда на сессию
5. Нет вложенных команд (teammates не могут создавать свои teams)
6. Lead фиксирован на всё время жизни команды
7. Permissions устанавливаются при spawn
8. Split panes только в tmux или iTerm2

### Отличие от Subagents

| | Subagents | Agent Teams |
|---|---|---|
| Контекст | Свой; результаты возвращаются caller | Свой; полностью независимые |
| Коммуникация | Только обратно к main agent | Teammates общаются напрямую |
| Координация | Main agent управляет всем | Shared task list с self-coordination |
| Лучше для | Фокусированные задачи | Сложная работа с обсуждением |
| Стоимость | Ниже | Выше |

---

## 2. Addy Osmani — Claude Code Swarms

**Источник:** https://addyosmani.com/blog/claude-code-agent-teams/

Addy Osmani (Google) описывает Agent Teams как "swarms" — продвинутую модель оркестрации, где множество Claude Code экземпляров работают параллельно. Ключевые наблюдения:
- Каждый sub-agent работает в собственном tmux pane
- Подходит для cross-layer координации (frontend + backend + tests)
- Основная ценность: параллельная эксплорация с взаимным вызовом

---

## 3. Daniel Avila — Agent Teams in Claude Code (Medium)

**Источник:** https://medium.com/@dan.avila7/agent-teams-in-claude-code-d6bb90b3333b

Практический обзор Agent Teams от разработчика:
- Появились с релизом Opus 4.6
- Teammates share a task list, claim work, communicate directly
- Принципиальное отличие от subagents: subagents только отчитываются main agent, teammates общаются между собой

---

## 4. Cobus Greyling — Claude Code Agent Teams (Medium)

**Источник:** https://cobusgreyling.medium.com/claude-code-agent-teams-ca3ec5f2d26a

- Getting Started guide
- Подчёркивает что Agent Teams = experimental feature
- Описывает lead/teammate модель
- Отмечает необходимость CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1

---

## 5. Turing College — Claude Agent Teams Explained

**Источник:** https://www.turingcollege.com/blog/claude-agent-teams-explained

AI для сложных проектов, гайд 2026:
- Agent Teams как следующий шаг после single-agent workflows
- Масштабирование через параллельную работу
- Best use cases: research, code review, debugging

---

## 6. SitePoint — Claude Code Agent Teams: Run Parallel AI Agents

**Источник:** https://www.sitepoint.com/anthropic-claude-code-agent-teams/

Setup & Guide:
- Пошаговая настройка
- Запуск параллельных агентов на codebase
- Практические примеры

---

## 7. alexop.dev — From Tasks to Swarms

**Источник:** https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/

Описание эволюции от задач к swarm-архитектуре в Claude Code:
- Исторический контекст: subagents → agent teams
- Task system как основа координации
- Swarm patterns

---

## 8. paddo.dev — Claude Code's Hidden Multi-Agent System

**Источник:** https://paddo.dev/blog/claude-code-hidden-swarm/

Раскрытие "скрытой" мультиагентной системы:
- Описание внутренних механизмов Agent Teams
- Архитектурные паттерны

---

## 9. GitHub Issues и обсуждения

**Источник:** https://github.com/anthropics/claude-code/issues/23615

Issue: "Agent teams should spawn in new tmux window, not split current pane"
- Обсуждение UX split-pane vs new window
- Feedback от сообщества по поведению tmux интеграции

---

## 10. Agent Definition Files (.claude/agents/)

**Источник:** https://code.claude.com/docs/en/sub-agents

- Файлы определения агентов хранятся в `.claude/agents/`
- Формат: Markdown с YAML frontmatter
- Поля frontmatter: name, description, tools, model
- Это для subagents, а не для Agent Teams напрямую
- Agent Teams создаются через natural language prompt, а не через файлы определения
- Однако teammates при запуске загружают проектный контекст включая CLAUDE.md и agents/

---

## 11. Стоимость и экономика

**Источник:** https://code.claude.com/docs/en/costs

- Claude Code ~$100-200/dev/month с Sonnet 4.6
- Agent Teams ~3-4x токенов одной сессии для 3 teammates
- В plan mode ~7x больше токенов
- Оптимизация: разные модели для разных teammates (Opus для reasoning, Sonnet для implementation)
- Экономия 40-60% при смешанных моделях

---

## 12. Eric Buess (Twitter/X)

**Источник:** https://x.com/EricBuess/status/2028217923760959976

Наблюдение: новые версии Claude Code корректно завершают agent team member panes в tmux и очищают всё в UI при работе внутри tmux в iTerm.
