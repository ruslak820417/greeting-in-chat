# Visual Plan: Claude Code Agent Teams

> Автор: visual-director
> Статус: FINAL v1
> Дата: 2026-03-19

---

## Визуальный язык эпизода

**Палитра:** Тёмный терминальный фон (#1a1b26) + неоновые акценты для каждого агента:
- showrunner: 🟡 жёлтый (#e0af68)
- web-researcher: 🔵 синий (#7aa2f7)
- fact-checker: 🟢 зелёный (#9ece6a)
- script-architect: 🟣 фиолетовый (#bb9af7)
- visual-director: 🔴 красный (#f7768e)
- pdf-producer: 🟠 оранжевый (#ff9e64)

**Типографика:** Monospace (JetBrains Mono / Fira Code) для терминала, Inter/SF Pro для оверлеев и заголовков.

**Стиль:** Cyberpunk terminal aesthetic — тёмный фон, светящиеся линии коммуникации между агентами, particle effects при handoff.

---

## Thumbnail

### Вариант A (рекомендуемый)
- **Композиция:** Центральный экран с 6 tmux-панелями, каждая подсвечена цветом агента
- **Текст:** "6 AI-АГЕНТОВ" крупно + "Работают ВМЕСТЕ" мельче
- **Акцент:** Светящиеся линии соединяют панели, показывая коммуникацию
- **Лицо:** Автор сбоку с выражением удивления (YouTube CTR boost)

### Вариант B
- **Композиция:** Схема hub-and-spoke — showrunner в центре, 5 агентов вокруг
- **Текст:** "Claude КЛОНИРОВАЛ СЕБЯ"
- **Акцент:** Стрелки между агентами, каждый с иконкой роли

---

## Интро-сцена (0:00–0:03)

**Flash-тизер:**
- 2 секунды: быстрый зум на tmux-экран с 6 работающими панелями
- Glitch-transition на чёрный
- 1 секунда: появление заголовка "AGENT TEAMS"
- Звук: typing keyboard + digital whoosh

---

## Визуальная поддержка по сценам

### Сцена 1: HOOK (0:00–0:30)
| Момент | Визуал | Тип |
|--------|--------|-----|
| 0:00–0:03 | Flash tmux с 6 панелями | Screen capture |
| 0:03–0:15 | Автор в кадре, закадровый текст | Talking head |
| 0:15–0:30 | B-roll: zoom на tmux, агенты печатают | Screen capture |

### Сцена 2: ПОЧЕМУ СЕЙЧАС (0:30–1:30)
| Момент | Визуал | Тип |
|--------|--------|-----|
| 0:30–0:45 | Инфографика: "1 человек ↔ 1 AI" | Motion graphics |
| 0:45–1:00 | Анимация трансформации: 1 AI → 6 AI-агентов | Motion graphics |
| 1:00–1:15 | Логотипы: Copilot, Cursor (перечёркнуты) vs Claude (галочка) | Overlay |
| 1:15–1:30 | Timeline AI-coding tools → Agent Teams как новый шаг | Infographic |

### Сцена 3: ЧТО ТАКОЕ (1:30–3:30)
| Момент | Визуал | Тип |
|--------|--------|-----|
| 1:30–2:00 | Схема 4 компонентов: Lead, Teammates, Task List, Mailbox | Diagram |
| 2:00–2:30 | Анимация: subagents (линейные стрелки) vs Agent Teams (сетка) | Motion graphics |
| 2:30–3:00 | Screencast: содержимое `.claude/agents/`, открытие showrunner.md | Screen capture |
| 3:00–3:30 | Аналогия: иконки фрилансеров → иконки AI-агентов | Illustration |

**Overlay:** Постоянный лейбл "EXPERIMENTAL FEATURE" в углу при первом упоминании.

### Сцена 4: КАК РАБОТАЕТ (3:30–6:30)
| Момент | Визуал | Тип |
|--------|--------|-----|
| 3:30–4:00 | Screencast: settings.json, env flag, tmux config | Screen capture |
| 4:00–4:30 | Screencast: `tmux new -s claude-agent-team` → `claude` | Screen capture |
| 4:30–5:00 | Экран делится на 6 панелей, агенты появляются | Screen capture + overlay |
| 5:00–5:30 | Split-screen: researcher (слева) и visual-director (справа) работают параллельно | Screen capture |
| 5:30–6:00 | Zoom: файлы появляются в agent-runtime/shared/ | Screen capture |
| 6:00–6:15 | Анимация: handoff стрелка researcher → fact-checker | Motion graphics overlay |
| 6:15–6:30 | Screencast: fact-checker проверяет, ставит ✅ approved | Screen capture |

**UI Overlay:** Цветная рамка вокруг каждой tmux-панели с именем агента и статусом (WORKING / IDLE / DONE).

### Сцена 5: PROOF (6:30–8:30)
| Момент | Визуал | Тип |
|--------|--------|-----|
| 6:30–7:00 | VS Code / файловый менеджер: список файлов outputs/ | Screen capture |
| 7:00–7:30 | Zoom на research-summary.md — ключевые находки подсвечены | Screen capture |
| 7:30–7:50 | Zoom на verified-claims.md — таблица с ✅ | Screen capture |
| 7:50–8:10 | Zoom на video-script.md — структура скрипта | Screen capture |
| 8:10–8:30 | Side-by-side: ПУСТАЯ папка agent-runtime → ЗАПОЛНЕННАЯ | Split-screen |

### Сцена 6: ИТОГ + CTA (8:30–9:30)
| Момент | Визуал | Тип |
|--------|--------|-----|
| 8:30–9:00 | Автор в кадре, recap ключевых моментов | Talking head |
| 9:00–9:15 | Recap-монтаж: 4 лучших момента из видео (2 сек каждый) | Montage |
| 9:15–9:30 | End screen: подписка, видео, вопрос в комментариях | End card |

---

## Диаграммы и UI Overlays

### Диаграмма 1: Архитектура Agent Teams
```
         ┌─────────────┐
         │  SHOWRUNNER  │  ← Lead
         │   (yellow)   │
         └──────┬───────┘
                │
    ┌───────────┼───────────┐
    │           │           │
    ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐
│RESEARCH│ │  FACT  │ │ SCRIPT │
│ (blue) │ │(green) │ │(purple)│
└────┬───┘ └────┬───┘ └────┬───┘
     │          │           │
     └──────────┼───────────┘
                │
    ┌───────────┼───────────┐
    │                       │
    ▼                       ▼
┌────────┐           ┌────────┐
│ VISUAL │           │  PDF   │
│ (red)  │           │(orange)│
└────────┘           └────────┘
```

### Диаграмма 2: Workflow зависимостей
```
web-researcher ──→ fact-checker ──→ script-architect
       │                                    │
       └──→ visual-director ────────────────┘
                                            │
                                     pdf-producer
```

### UI Overlay: Agent Status Bar
```
┌──────────────────────────────────────────────┐
│ 🟡 showrunner: COORDINATING                  │
│ 🔵 web-researcher: DONE ✅                   │
│ 🟢 fact-checker: VERIFYING...                │
│ 🟣 script-architect: WAITING                 │
│ 🔴 visual-director: DONE ✅                  │
│ 🟠 pdf-producer: WAITING                     │
└──────────────────────────────────────────────┘
```

---

## Рекомендации по монтажу

1. **Темп:** быстрый в hook и proof, медленнее в объяснениях
2. **Transitions:** glitch-эффект при переключении между агентами
3. **Sound design:** subtle keyboard typing во время screen capture
4. **Zoom:** используй 150-200% zoom на ключевые строки кода/файлов
5. **Color grading:** холодные тона для терминала, тёплые для talking head
