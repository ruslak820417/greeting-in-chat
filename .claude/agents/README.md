# Роли Claude Agent Team

В этой папке лежат инструкции ролей для наглядного мультиагентного процесса в Claude Agent Teams.

## Рекомендуемый состав команды

- `showrunner.md`: супервайзер и планировщик процесса
- `web-researcher.md`: ищет источники и извлекает тезисы
- `fact-checker.md`: проверяет тезисы и отмечает слабые доказательства
- `script-architect.md`: превращает проверенный материал в YouTube-нарратив
- `visual-director.md`: придумывает сцены, концепции превью и промпты для изображений
- `pdf-producer.md`: собирает финальные материалы в отчет, готовый к экспорту в PDF

## Контракт коммуникации

Все агенты взаимодействуют через общие артефакты и явные handoff-сообщения.

- Общие входные данные и рабочие файлы лежат в `agent-runtime/shared/`
- Статус и служебные заметки лежат в `agent-runtime/state/`
- Сообщения между агентами лежат в `agent-runtime/messages/`
- Финальные результаты лежат в `agent-runtime/outputs/`

Каждое handoff-сообщение должно содержать:

```md
id: msg-001
from: showrunner
to: web-researcher
type: assignment
topic: AI agents for YouTube demo
artifacts:
  - agent-runtime/shared/brief.md
needs:
  - 5-7 source-backed claims
deadline: immediate
```

## Рекомендуемый сценарий демо

1. `showrunner` читает brief и публикует план.
2. `web-researcher` и `visual-director` стартуют параллельно.
3. `web-researcher` передает тезисы агенту `fact-checker`.
4. `fact-checker` публикует пакет проверенных тезисов.
5. `script-architect` пишет нарратив, используя проверенные тезисы и визуальные идеи.
6. `pdf-producer` собирает финальный пакет для презентации.

Этот паттерн делает процесс читаемым на видео и показывает реальное взаимодействие между агентами.
