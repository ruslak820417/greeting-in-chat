#!/usr/bin/env python3
"""Generate video-script PDF for Claude Code Agent Teams YouTube demo."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether, Flowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Font ---
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
pdfmetrics.registerFont(TTFont("ArialUnicode", FONT_PATH))
F = "ArialUnicode"

# --- Colors ---
DARK = HexColor("#1a1a2e")
ACCENT = HexColor("#e17055")       # warm orange for script
ACCENT_DARK = HexColor("#d63031")
ACCENT_LIGHT = HexColor("#fab1a0")
BLUE = HexColor("#0984e3")
TEAL = HexColor("#00cec9")
GRAY = HexColor("#636e72")
LIGHT_GRAY = HexColor("#dfe6e9")
VISUAL_BG = HexColor("#fff3e0")    # warm tint for visual directions
CODE_BG = HexColor("#f0f0f0")
WHITE = white

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PDF = os.path.join(SCRIPT_DIR, "video-script.pdf")


class ColorBar(Flowable):
    """A colored bar with text label, used for section headers."""
    def __init__(self, text, timecode, bg_color, width=None):
        super().__init__()
        self.text = text
        self.timecode = timecode
        self.bg = bg_color
        self._width = width or 170 * mm

    def wrap(self, aW, aH):
        self._width = aW
        return aW, 28

    def draw(self):
        self.canv.setFillColor(self.bg)
        self.canv.roundRect(0, 0, self._width, 26, 4, fill=1, stroke=0)
        self.canv.setFillColor(WHITE)
        self.canv.setFont(F, 13)
        self.canv.drawString(12, 7, self.text)
        self.canv.setFont(F, 10)
        self.canv.drawRightString(self._width - 12, 8, self.timecode)


def styles():
    return {
        "title": ParagraphStyle(
            "Title", fontName=F, fontSize=26, leading=32,
            textColor=WHITE, alignment=TA_CENTER, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "Sub", fontName=F, fontSize=12, leading=16,
            textColor=HexColor("#dfe6e9"), alignment=TA_CENTER,
        ),
        "h2": ParagraphStyle(
            "H2", fontName=F, fontSize=13, leading=17,
            textColor=ACCENT_DARK, spaceBefore=10, spaceAfter=4,
        ),
        "voiceover": ParagraphStyle(
            "VO", fontName=F, fontSize=11, leading=16,
            textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=6,
            leftIndent=4, rightIndent=4,
        ),
        "visual": ParagraphStyle(
            "Vis", fontName=F, fontSize=9.5, leading=14,
            textColor=HexColor("#6c5ce7"), alignment=TA_LEFT,
            leftIndent=14, rightIndent=14, spaceBefore=4, spaceAfter=6,
            backColor=VISUAL_BG, borderPadding=6,
        ),
        "quote": ParagraphStyle(
            "Quote", fontName=F, fontSize=10.5, leading=15,
            textColor=HexColor("#2d3436"), alignment=TA_LEFT,
            leftIndent=20, rightIndent=20, spaceBefore=4, spaceAfter=6,
            borderColor=ACCENT, borderWidth=0, borderPadding=4,
        ),
        "code": ParagraphStyle(
            "Code", fontName=F, fontSize=9, leading=13,
            textColor=HexColor("#2d3436"), backColor=CODE_BG,
            leftIndent=14, rightIndent=14, spaceBefore=4, spaceAfter=6,
            borderPadding=6,
        ),
        "meta": ParagraphStyle(
            "Meta", fontName=F, fontSize=8.5, leading=12,
            textColor=GRAY, alignment=TA_LEFT, spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "Footer", fontName=F, fontSize=8, leading=10,
            textColor=GRAY, alignment=TA_CENTER,
        ),
        "th": ParagraphStyle(
            "TH", fontName=F, fontSize=9, leading=12,
            textColor=WHITE, alignment=TA_CENTER,
        ),
        "td": ParagraphStyle(
            "TD", fontName=F, fontSize=9, leading=12,
            textColor=DARK, alignment=TA_LEFT,
        ),
        "td_c": ParagraphStyle(
            "TDc", fontName=F, fontSize=9, leading=12,
            textColor=DARK, alignment=TA_CENTER,
        ),
    }


def cover_page(c, doc):
    w, h = A4
    c.setFillColor(DARK)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    # Accent stripe
    c.setFillColor(ACCENT)
    c.rect(0, h * 0.44, w, 5, fill=1, stroke=0)
    # Bottom bar
    c.setFillColor(ACCENT_LIGHT)
    c.rect(0, 0, w, 8, fill=1, stroke=0)


def later_page(c, doc):
    w, h = A4
    # Top bar
    c.setFillColor(ACCENT_DARK)
    c.rect(0, h - 12 * mm, w, 12 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(F, 9)
    c.drawString(18 * mm, h - 8.5 * mm, "VIDEO SCRIPT  —  Claude Code Agent Teams")
    c.drawRightString(w - 18 * mm, h - 8.5 * mm, "~9-10 min  |  2026-03-13")
    # Bottom
    c.setFillColor(ACCENT)
    c.rect(0, 0, w, 5 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(F, 7)
    c.drawCentredString(w / 2, 1.5 * mm, f"— {doc.page} —")


def build():
    s = styles()
    doc = SimpleDocTemplate(
        OUTPUT_PDF, pagesize=A4,
        topMargin=20 * mm, bottomMargin=14 * mm,
        leftMargin=18 * mm, rightMargin=18 * mm,
    )
    story = []

    # ============ COVER ============
    story.append(Spacer(1, 70 * mm))
    story.append(Paragraph("VIDEO SCRIPT", s["subtitle"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("CLAUDE CODE<br/>AGENT TEAMS", s["title"]))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("YouTube Demo  |  ~9-10 минут  |  2026-03-13", s["subtitle"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Автор: script-architect<br/>Статус: DRAFT v2 (research + verified claims integrated)", s["subtitle"]))
    story.append(Spacer(1, 25 * mm))
    story.append(Paragraph(
        "Закадровый текст  |  Визуальные метки  |  Технические пометки для монтажа", s["subtitle"]
    ))
    story.append(PageBreak())

    # ============ SECTION 1: HOOK ============
    story.append(ColorBar("HOOK", "0:00 — 0:30", ACCENT_DARK))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Anthropic только что выпустил фичу, которую я не ожидал увидеть ещё минимум год.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Они превратили Claude Code из одиночного AI-ассистента — в оркестратор целой команды "
        "агентов. Каждый — со своей ролью. Каждый — со своим контекстом. И они реально "
        "общаются друг с другом.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Это называется Agent Teams. И сегодня я покажу вам, как это работает — "
        "не на слайдах, а вживую.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: быстрый тизер — экран с 6 tmux-панелями, агенты работают параллельно. "
        "2-3 секунды, без пояснений — просто впечатление.",
        s["visual"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ============ SECTION 2: ПОЧЕМУ СЕЙЧАС ============
    story.append(ColorBar("ПОЧЕМУ СЕЙЧАС", "0:30 — 1:30", BLUE))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Давайте честно. AI-ассистенты для кода — это уже не новость. Copilot, Cursor, "
        "Claude Code — все они умеют писать и редактировать код по запросу.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        'Но до сих пор это была модель "один человек — один ассистент". Ты пишешь промпт, '
        "получаешь ответ, двигаешься дальше.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Agent Teams меняют эту парадигму. Вместо одного агента ты запускаешь команду. "
        "Один ищет информацию в интернете. Другой проверяет факты. Третий пишет сценарий. "
        "Четвёртый готовит визуалы. И пятый собирает всё в финальный отчёт.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "И всё это — параллельно. В одном терминале. Без твоего вмешательства на каждом шаге.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Ни Cursor, ни Copilot пока не предложили ничего подобного. Anthropic здесь первый.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        'ВИЗУАЛ: простая анимация — от "1 человек &lt;-&gt; 1 AI" к '
        '"1 человек -> AI-команда из 6 агентов".',
        s["visual"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ============ SECTION 3: ЧТО ТАКОЕ ============
    story.append(ColorBar("ЧТО ТАКОЕ AGENT TEAMS", "1:30 — 3:30", HexColor("#6c5ce7")))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Окей, давайте разберёмся, что это технически.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Agent Teams — это экспериментальная функция Claude Code, которая появилась вместе "
        "с релизом Opus 4.6. Она позволяет координировать несколько независимых экземпляров "
        "Claude Code, работающих параллельно над общим проектом с межагентной коммуникацией.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "У системы четыре ключевых компонента. Первый — Team Lead. Это главная сессия, "
        "которая создаёт команду и координирует работу. Второй — Teammates. Это отдельные "
        "экземпляры Claude Code, каждый со своим context window. Третий — Task List. Общий "
        "список задач с зависимостями и автоматической разблокировкой. И четвёртый — Mailbox. "
        "Система обмена сообщениями между агентами.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: схема четырёх компонентов — Lead, Teammates, Task List, Mailbox.",
        s["visual"],
    ))
    story.append(Paragraph(
        "И вот что важно понять. Это не subagents. У Claude Code уже были subagents — но они "
        "только отчитывались основному агенту и не могли общаться друг с другом. В Agent Teams "
        "всё иначе: teammates общаются напрямую, делят общий task list и координируются "
        "самостоятельно. Это принципиальный архитектурный скачок.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Роли агентов описаны в простых markdown-файлах — в папке .claude/agents/. Каждый файл "
        "задаёт контракт: миссия, обязанности, что агент должен создать. При этом все teammates "
        "загружают общий проектный контекст — CLAUDE.md, MCP-серверы, skills — но не наследуют "
        "историю диалога от lead. Важный контекст передаётся через spawn prompt.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Ключевой механизм коммуникации — SendMessage. Два типа: message — отправка конкретному "
        "teammate, и broadcast — отправка всем сразу. Broadcast используется экономно, потому что "
        "стоимость масштабируется с размером команды. Сообщения доставляются автоматически — "
        "lead не нужно вручную проверять почтовый ящик.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "И вот что делает это визуально впечатляющим: Agent Teams поддерживают два режима "
        "отображения. In-process — всё в одном терминале, переключение через Shift+Down. И "
        "split panes — каждый teammate в своей панели. Для split panes нужен tmux или iTerm2. "
        "И когда ты видишь шесть агентов, работающих одновременно в шести панелях — это впечатляет.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Представьте, что вы наняли команду фрилансеров. Дали каждому задачу. И они сами "
        "координируются между собой — передают файлы, проверяют работу друг друга, собирают "
        "финальный результат. Только вместо людей — AI-агенты. И вместо дней — минуты.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: скриншот реального tmux с подписями ролей над каждой панелью.",
        s["visual"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ============ SECTION 4: КАК ЭТО РАБОТАЕТ ============
    story.append(ColorBar("КАК ЭТО РАБОТАЕТ", "3:30 — 6:30", HexColor("#00b894")))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Теперь — самое интересное. Давайте запустим это вживую.",
        s["voiceover"],
    ))

    # -- Настройка --
    story.append(Paragraph("<b>Настройка  [3:30-4:00]</b>", s["h2"]))
    story.append(Paragraph(
        "Для начала — минимальные требования. Нужен Claude Code версии 2.1.32 или новее. "
        "В настройках проекта включаем экспериментальный флаг:",
        s["voiceover"],
    ))
    story.append(Paragraph(
        '"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"',
        s["code"],
    ))
    story.append(Paragraph(
        "И устанавливаем режим teammates в tmux:",
        s["voiceover"],
    ))
    story.append(Paragraph(
        '"teammateMode": "tmux"',
        s["code"],
    ))
    story.append(Paragraph(
        "По умолчанию teammateMode стоит в auto — split panes, если вы уже в tmux, иначе "
        "in-process. Мы явно ставим tmux, потому что для демо нам нужны видимые панели.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Важный нюанс: split panes не поддерживаются в VS Code integrated terminal, "
        "Windows Terminal и Ghostty. Только tmux и iTerm2.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Дальше — роли. В папке .claude/agents/ лежат markdown-файлы. Каждый файл описывает "
        "одного специалиста: его миссию, обязанности и выходные артефакты.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: показать содержимое папки agents/, открыть один файл — например showrunner.md.",
        s["visual"],
    ))

    # -- Запуск --
    story.append(Paragraph("<b>Запуск команды  [4:00-5:00]</b>", s["h2"]))
    story.append(Paragraph(
        "Открываем tmux. Запускаем Claude Code. И даём ему инструкцию на естественном языке:",
        s["voiceover"],
    ))
    story.append(Paragraph(
        '"Создай команду для подготовки YouTube-видео. Используй ролей: showrunner, '
        'web-researcher, fact-checker, script-architect, visual-director и pdf-producer."',
        s["quote"],
    ))
    story.append(Paragraph(
        "И вот тут начинается магия.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: экран делится на панели, в каждой появляется свой агент.",
        s["visual"],
    ))
    story.append(Paragraph(
        "Lead-агент — showrunner — получает задачу. Он составляет план. Распределяет работу. "
        "И запускает первых исполнителей.",
        s["voiceover"],
    ))

    # -- Параллельная работа --
    story.append(Paragraph("<b>Параллельная работа  [5:00-5:45]</b>", s["h2"]))
    story.append(Paragraph(
        "Смотрите — web-researcher и visual-director стартуют одновременно. В левой панели "
        "researcher ищет информацию по теме. В правой — visual-director продумывает сцены "
        "и визуальные промпты.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Это не последовательная цепочка. Это параллельное выполнение. Два агента работают "
        "независимо, каждый в своём контексте. Задачи имеют три состояния — pending, "
        "in_progress, completed — и система поддерживает dependency tracking с автоматической "
        "разблокировкой. А чтобы два агента не схватили одну задачу, используется file locking.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Через пару минут в папке agent-runtime/shared/ появляются файлы: "
        "research-summary.md и visual-plan.md.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: split-screen двух панелей tmux, затем zoom на появившиеся файлы.",
        s["visual"],
    ))

    # -- Зависимости --
    story.append(Paragraph("<b>Зависимости и коммуникация  [5:45-6:30]</b>", s["h2"]))
    story.append(Paragraph(
        "А вот здесь — самый интересный момент. Web-researcher закончил. Он отправляет "
        'сообщение fact-checker\'у: "Вот мои тезисы, проверь."',
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Fact-checker получает сообщение, читает research-summary, и начинает проверку. "
        "Он может одобрить тезис, отклонить или отправить на доработку.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        'Только после того, как тезисы получают статус "approved", они попадают к '
        "script-architect'у. И он строит историю только на проверенных фактах.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Кстати, lead может включить Plan Approval режим для любого teammate. В этом режиме "
        "teammate сначала составляет план в read-only mode, и lead одобряет или отклоняет его "
        "с обратной связью — только потом начинается реализация. Это даёт серьёзный уровень контроля.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Это ключевой момент: агенты не просто работают параллельно — они зависят друг от "
        "друга. Как настоящая команда.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: анимация handoff — стрелка от researcher -> fact-checker -> script-architect.",
        s["visual"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ============ SECTION 5: PROOF ============
    story.append(ColorBar("PROOF-МОМЕНТ", "6:30 — 8:30", HexColor("#fdcb6e")))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Окей, но работает ли это на самом деле? Давайте посмотрим на результаты.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: переключение на файловый менеджер или VS Code.",
        s["visual"],
    ))
    story.append(Paragraph(
        "Вот что создала команда агентов за один прогон:",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Первое — research-summary.md. Это сводка того, что нашёл web-researcher. "
        "Ключевые факты, ссылки на источники, контекст.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Второе — verified-claims.md. Это результат работы fact-checker'а. Каждый тезис "
        "помечен: approved, needs revision или rejected. В финальный скрипт попадают только approved.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Третье — video-script.md. Полный сценарий видео с закадровым текстом, "
        "визуальными метками и хронометражем.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Четвёртое — visual-plan.md и image-prompts.md. Визуальные сцены и промпты "
        "для генерации изображений.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "И наконец — final-report.md. Pdf-producer собрал всё в единый документ, "
        "готовый к экспорту.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: быстрое пролистывание всех файлов, zoom на ключевые секции.",
        s["visual"],
    ))
    story.append(Paragraph(
        "Шесть агентов. Один запуск. Материал для целого видео — за несколько минут.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "И главное — это не постановка. Вы видели, как агенты работали в реальном времени. "
        "Каждый файл создан конкретным агентом, с конкретной ролью, в конкретном контексте.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: side-by-side — пустая папка agent-runtime ДО запуска и заполненная ПОСЛЕ.",
        s["visual"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ============ SECTION 6: ИТОГ + CTA ============
    story.append(ColorBar("ИТОГ + CTA", "8:30 — 9:30", DARK))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Давайте подведём итог.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        'Agent Teams — это не просто "несколько промптов в одном проекте". Это полноценный '
        'shift. От модели "один человек — один ассистент" к модели "один человек — AI-команда".',
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Да, это пока экспериментальная функция. Да, она требует tmux и немного настройки. "
        "И да — есть ограничения. Нет session resumption для in-process teammates. Одна "
        "команда на сессию. Нет вложенных команд. Lead фиксирован на весь lifetime. "
        "Но даже в таком виде — это уже работает.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "По стоимости: команда из трёх teammates потребляет примерно в 3-4 раза больше "
        "токенов, чем одна сессия. Но есть лайфхак — можно назначать разные модели разным "
        "teammates. Opus для reasoning-задач, Sonnet для implementation. Это экономит 40-60% "
        "на токенах. Оптимальный размер команды — 3-5 teammates с 5-6 задачами на каждого.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Подумайте: сегодня мы показали контент-продакшн. Но по документации Anthropic, "
        "лучшие use cases — это research &amp; review, новые модули и фичи, debugging с "
        "конкурирующими гипотезами, и cross-layer координация — frontend, backend и тесты "
        "одновременно. Везде, где нужна команда с разными компетенциями.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Один человек. Команда AI-агентов. Результат за минуты.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Если хотите попробовать сами — ссылки на документацию и этот проект в описании. "
        "А в комментариях напишите: какую команду агентов вы бы собрали первой?",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "Подписывайтесь, ставьте лайк, и до встречи в следующем видео.",
        s["voiceover"],
    ))
    story.append(Paragraph(
        "ВИЗУАЛ: recap-монтаж — 3-4 ключевых момента из видео, финальная заставка с CTA.",
        s["visual"],
    ))
    story.append(PageBreak())

    # ============ APPENDIX: МОНТАЖНЫЕ МЕТКИ ============
    story.append(ColorBar("ТЕХНИЧЕСКИЕ МЕТКИ ДЛЯ МОНТАЖА", "", GRAY))
    story.append(Spacer(1, 6 * mm))

    edit_data = [
        [
            Paragraph("<b>Таймкод</b>", s["th"]),
            Paragraph("<b>Секция</b>", s["th"]),
            Paragraph("<b>Тип визуала</b>", s["th"]),
        ],
        [Paragraph("0:00-0:03", s["td_c"]), Paragraph("Тизер", s["td"]),
         Paragraph("Быстрый flash tmux-экрана", s["td"])],
        [Paragraph("0:03-0:30", s["td_c"]), Paragraph("Hook", s["td"]),
         Paragraph("Автор в кадре / voiceover", s["td"])],
        [Paragraph("0:30-1:30", s["td_c"]), Paragraph("Почему сейчас", s["td"]),
         Paragraph("Анимация / инфографика", s["td"])],
        [Paragraph("1:30-2:30", s["td_c"]), Paragraph("Архитектура", s["td"]),
         Paragraph("Схема lead / teammates", s["td"])],
        [Paragraph("2:30-3:30", s["td_c"]), Paragraph("Как устроено", s["td"]),
         Paragraph("Скриншоты agents/, CLAUDE.md", s["td"])],
        [Paragraph("3:30-4:00", s["td_c"]), Paragraph("Настройка", s["td"]),
         Paragraph("Screencast настроек", s["td"])],
        [Paragraph("4:00-5:00", s["td_c"]), Paragraph("Запуск", s["td"]),
         Paragraph("Screencast tmux", s["td"])],
        [Paragraph("5:00-6:30", s["td_c"]), Paragraph("Работа агентов", s["td"]),
         Paragraph("Screencast с zoom-in", s["td"])],
        [Paragraph("6:30-8:30", s["td_c"]), Paragraph("Proof", s["td"]),
         Paragraph("Файлы + side-by-side", s["td"])],
        [Paragraph("8:30-9:30", s["td_c"]), Paragraph("Итог + CTA", s["td"]),
         Paragraph("Автор в кадре + заставка", s["td"])],
    ]
    edit_table = Table(edit_data, colWidths=[70, 110, 255], repeatRows=1)
    edit_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), F),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#f8f8f8")]),
        ("GRID", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT),
    ]))
    story.append(edit_table)
    story.append(Spacer(1, 8 * mm))

    # Status
    story.append(Paragraph("<b>Статус интеграции:</b>", s["h2"]))
    checks = [
        "verified-claims.md от fact-checker — 14/15 тезисов approved (high confidence)",
        "research-summary.md от web-researcher — 15 тезисов, 12 источников",
        "Конкретные факты из ресерча интегрированы в секции 3, 4, 6",
    ]
    for ch in checks:
        story.append(Paragraph(f"[x]  {ch}", s["meta"]))
    story.append(Paragraph(
        "[ ]  Ожидает: visual-plan.md от visual-director (визуальные метки)",
        s["meta"],
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Скрипт подготовлен script-architect на основе verified claims от fact-checker "
        "и research-summary от web-researcher.",
        s["meta"],
    ))

    # ============ BUILD ============
    doc.build(story, onFirstPage=cover_page, onLaterPages=later_page)
    print(f"PDF generated: {OUTPUT_PDF}")


if __name__ == "__main__":
    build()
