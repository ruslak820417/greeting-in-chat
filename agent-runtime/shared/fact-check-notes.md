# Fact-Check Notes — Процесс верификации

**Дата:** 2026-03-13
**Агент:** fact-checker

---

## Методология

1. Проведён веб-поиск по каждому из 5 тезисов (4 параллельных запроса)
2. Загружена и проанализирована полная официальная документация: https://code.claude.com/docs/en/agent-teams
3. Каждый тезис сверен с точными формулировками документации
4. Дополнительно проверены issues на GitHub (anthropics/claude-code) для выявления известных багов

## Источники

### Первичные (official)
- **Официальная документация:** https://code.claude.com/docs/en/agent-teams
- **Anthropic engineering blog:** https://www.anthropic.com/engineering/building-c-compiler (case study: C compiler with agent teams)

### Вторичные (community, подтверждают official)
- https://claudefa.st/blog/guide/agents/agent-teams
- https://alexop.dev/posts/from-tasks-to-swarms-agent-teams-in-claude-code/
- https://addyosmani.com/blog/claude-code-agent-teams/
- https://cuttlesoft.com/blog/2026/02/24/setting-up-claude-code-agent-teams-on-macos/

### GitHub Issues (известные баги, актуальные для demo)
- #24292 — teammateMode "tmux" может не триггерить iTerm2 split panes
- #24301 — iTerm2 native split pane fallback в in-process
- #23615 — agent teams spawn в новом tmux window вместо split pane
- #24771 — split panes открываются, но teammates disconnected от messaging
- #24385 — iTerm2 panes не закрываются при shutdown teammate

## Дополнительные факты (не в тезисах, но важны для скрипта)

1. **Версия:** требуется Claude Code v2.1.32+
2. **Token cost:** ~3-4x от single session для team из 3 teammates
3. **Рекомендуемый размер:** 3-5 teammates, 5-6 tasks per teammate
4. **Ограничения:**
   - No session resumption с in-process teammates
   - Task status может отставать
   - Shutdown может быть медленным
   - Один team per session
   - No nested teams
   - Lead фиксирован
   - Split panes не работают в VS Code terminal, Windows Terminal, Ghostty
5. **Отличие от subagents:** subagents — focused workers отчитывающиеся обратно; agent teams — teammates с прямой коммуникацией и shared task list
6. **Hooks:** TeammateIdle и TaskCompleted для quality gates
7. **Storage:** team config в `~/.claude/teams/{team-name}/config.json`, tasks в `~/.claude/tasks/{team-name}/`

## Риски для демо-контента

- Split pane mode имеет известные баги — может потребоваться fallback на in-process
- Нужно заранее проверить версию Claude Code (>= v2.1.32)
- Cleanup должен запускаться только через lead (не через teammates)
- При resumption in-process teammates не восстанавливаются

## Статус

Фаза 1 завершена. Все 5 тезисов подтверждены (approved, high confidence).
Ожидание research-summary.md для Фазы 2.
