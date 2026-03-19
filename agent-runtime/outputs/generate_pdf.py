#!/usr/bin/env python3
"""Generate final PDF report for Claude Code Agent Teams YouTube demo."""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Font setup ---
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
pdfmetrics.registerFont(TTFont("ArialUnicode", FONT_PATH))
FONT = "ArialUnicode"

# --- Colors ---
DARK = HexColor("#1a1a2e")
ACCENT = HexColor("#6c5ce7")
ACCENT_LIGHT = HexColor("#a29bfe")
GRAY = HexColor("#636e72")
LIGHT_BG = HexColor("#f5f5ff")
GREEN = HexColor("#00b894")
ORANGE = HexColor("#fdcb6e")
RED = HexColor("#d63031")
WHITE = white

# --- Output path ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PDF = os.path.join(SCRIPT_DIR, "final-report.pdf")


def get_styles():
    """Create paragraph styles for the report."""
    return {
        "title": ParagraphStyle(
            "Title", fontName=FONT, fontSize=24, leading=30,
            textColor=WHITE, alignment=TA_CENTER, spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", fontName=FONT, fontSize=12, leading=16,
            textColor=HexColor("#dfe6e9"), alignment=TA_CENTER, spaceAfter=4,
        ),
        "h1": ParagraphStyle(
            "H1", fontName=FONT, fontSize=18, leading=24,
            textColor=DARK, spaceBefore=16, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "H2", fontName=FONT, fontSize=14, leading=18,
            textColor=ACCENT, spaceBefore=12, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "H3", fontName=FONT, fontSize=11, leading=15,
            textColor=DARK, spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body", fontName=FONT, fontSize=10, leading=14,
            textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=6,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold", fontName=FONT, fontSize=10, leading=14,
            textColor=DARK, spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "Bullet", fontName=FONT, fontSize=10, leading=14,
            textColor=DARK, leftIndent=16, spaceAfter=4,
            bulletIndent=6, bulletFontSize=10,
        ),
        "small": ParagraphStyle(
            "Small", fontName=FONT, fontSize=8, leading=11,
            textColor=GRAY, spaceAfter=2,
        ),
        "table_header": ParagraphStyle(
            "TableHeader", fontName=FONT, fontSize=9, leading=12,
            textColor=WHITE, alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "TableCell", fontName=FONT, fontSize=9, leading=12,
            textColor=DARK, alignment=TA_LEFT,
        ),
        "table_cell_center": ParagraphStyle(
            "TableCellCenter", fontName=FONT, fontSize=9, leading=12,
            textColor=DARK, alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "Footer", fontName=FONT, fontSize=8, leading=10,
            textColor=GRAY, alignment=TA_CENTER,
        ),
        "code": ParagraphStyle(
            "Code", fontName=FONT, fontSize=9, leading=12,
            textColor=HexColor("#2d3436"), backColor=HexColor("#f0f0f0"),
            leftIndent=10, rightIndent=10, spaceBefore=4, spaceAfter=4,
        ),
    }


def cover_page(canvas_obj, doc):
    """Draw cover page background."""
    w, h = A4
    # Gradient-like background
    canvas_obj.setFillColor(DARK)
    canvas_obj.rect(0, 0, w, h, fill=1, stroke=0)
    # Accent strip
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, h * 0.42, w, 4, fill=1, stroke=0)
    # Bottom accent bar
    canvas_obj.setFillColor(ACCENT_LIGHT)
    canvas_obj.rect(0, 0, w, 8, fill=1, stroke=0)


def normal_page(canvas_obj, doc):
    """Draw header/footer on normal pages."""
    w, h = A4
    # Top bar
    canvas_obj.setFillColor(DARK)
    canvas_obj.rect(0, h - 14 * mm, w, 14 * mm, fill=1, stroke=0)
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont(FONT, 9)
    canvas_obj.drawString(20 * mm, h - 10 * mm, "Claude Code Agent Teams — Final Report")
    canvas_obj.drawRightString(w - 20 * mm, h - 10 * mm, "2026-03-13")
    # Bottom bar
    canvas_obj.setFillColor(ACCENT)
    canvas_obj.rect(0, 0, w, 6 * mm, fill=1, stroke=0)
    canvas_obj.setFillColor(WHITE)
    canvas_obj.setFont(FONT, 8)
    canvas_obj.drawCentredString(w / 2, 2 * mm, f"— {doc.page} —")


def build_pdf():
    """Build the complete PDF report."""
    s = get_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PDF, pagesize=A4,
        topMargin=22 * mm, bottomMargin=16 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
    )
    story = []

    # ============================================================
    # COVER PAGE
    # ============================================================
    story.append(Spacer(1, 80 * mm))
    story.append(Paragraph("CLAUDE CODE", s["subtitle"]))
    story.append(Paragraph("AGENT TEAMS", s["title"]))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Финальный отчёт мультиагентной системы", s["subtitle"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("YouTube Demo Project  |  2026-03-13", s["subtitle"]))
    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph(
        "Подготовлено командой из 6 AI-агентов:<br/>"
        "showrunner · web-researcher · fact-checker<br/>"
        "script-architect · visual-director · pdf-producer",
        s["subtitle"],
    ))
    story.append(PageBreak())

    # ============================================================
    # TABLE OF CONTENTS
    # ============================================================
    story.append(Paragraph("Содержание", s["h1"]))
    story.append(Spacer(1, 4 * mm))
    toc_items = [
        ("1.", "Резюме проекта"),
        ("2.", "Резюме исследования"),
        ("3.", "Проверенные тезисы"),
        ("4.", "YouTube Script Outline"),
        ("5.", "Ключевые выдержки из скрипта"),
        ("6.", "Архитектура Agent Teams"),
        ("7.", "Известные баги и риски"),
        ("8.", "Источники"),
    ]
    for num, title in toc_items:
        story.append(Paragraph(f"<b>{num}</b>  {title}", s["body"]))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT_LIGHT))
    story.append(PageBreak())

    # ============================================================
    # 1. РЕЗЮМЕ ПРОЕКТА
    # ============================================================
    story.append(Paragraph("1. Резюме проекта", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Этот отчёт подготовлен мультиагентной системой Claude Code Agent Teams "
        "в рамках демо-проекта для YouTube-контента. Цель проекта — наглядно показать, "
        "как несколько специализированных AI-агентов исследуют тему, проверяют факты, "
        "пишут сценарий, готовят визуалы и собирают итоговый пакет материалов.", s["body"]
    ))
    story.append(Paragraph("<b>Команда агентов:</b>", s["body_bold"]))

    roles = [
        ("showrunner", "управление командой и зависимостями"),
        ("web-researcher", "поиск и сбор материалов"),
        ("fact-checker", "проверка тезисов по первоисточникам"),
        ("script-architect", "структура и текст YouTube-видео"),
        ("visual-director", "визуальные сцены и image prompts"),
        ("pdf-producer", "сборка финального отчёта"),
    ]
    for role, desc in roles:
        story.append(Paragraph(f"• <b>{role}</b> — {desc}", s["bullet"]))
    story.append(Spacer(1, 4 * mm))

    # ============================================================
    # 2. РЕЗЮМЕ ИССЛЕДОВАНИЯ
    # ============================================================
    story.append(Paragraph("2. Резюме исследования", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Исследование проведено web-researcher, охватывает 15 тезисов из 12 источников.", s["body"]
    ))
    story.append(Paragraph("<b>Ключевые находки:</b>", s["body_bold"]))

    findings = [
        "<b>Agent Teams</b> — экспериментальная функция Claude Code, позволяющая координировать несколько "
        "независимых экземпляров Claude Code параллельно с межагентной коммуникацией. "
        "Требует CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 и Claude Code v2.1.32+.",

        "<b>Архитектура</b> из четырёх компонентов: Team Lead, Teammates, Task List, Mailbox.",

        "<b>Отличие от Subagents:</b> subagents только отчитываются основному агенту; "
        "в Agent Teams teammates общаются напрямую и координируются самостоятельно.",

        "<b>Два режима:</b> in-process (один терминал, Shift+Down) и split panes (tmux/iTerm2).",

        "<b>Task management:</b> pending / in_progress / completed, dependency tracking, file locking.",

        "<b>Контекст:</b> teammates загружают CLAUDE.md, MCP серверы, skills, но НЕ наследуют "
        "conversation history от lead.",

        "<b>Оптимальный размер:</b> 3–5 teammates, 5–6 задач на каждого. Стоимость ~3–4x.",

        "<b>Quality gates:</b> хуки TeammateIdle и TaskCompleted для автоматического feedback.",

        "<b>Лучшие use cases:</b> research &amp; review, новые модули, debugging, cross-layer координация.",
    ]
    for f in findings:
        story.append(Paragraph(f"• {f}", s["bullet"]))
    story.append(Spacer(1, 4 * mm))

    # ============================================================
    # 3. ПРОВЕРЕННЫЕ ТЕЗИСЫ
    # ============================================================
    story.append(Paragraph("3. Проверенные тезисы", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Верификация проведена fact-checker на основе официальной документации Anthropic.", s["body"]
    ))

    # Claims table
    claims_data = [
        [
            Paragraph("<b>#</b>", s["table_header"]),
            Paragraph("<b>Тезис</b>", s["table_header"]),
            Paragraph("<b>Статус</b>", s["table_header"]),
            Paragraph("<b>Доверие</b>", s["table_header"]),
        ],
    ]
    claims = [
        ("1", "Experimental + env var", "approved", "high"),
        ("2", "tmux / iTerm2 split panes", "approved", "high"),
        ("3", "Lead + teammates architecture", "approved", "high"),
        ("4", "SendMessage direct communication", "approved", "high"),
        ("5", "Parallel execution", "approved", "high"),
        ("6", "Task states + dependency + file locking", "approved", "high"),
        ("7", "Context loading, no history inheritance", "approved", "high"),
        ("8", "Opus 4.6 release = Agent Teams (Feb 2026)", "approved", "high"),
        ("9", "3-5 teammates, 5-6 tasks, 3-4x tokens", "approved", "high"),
        ("10", "Different models save 40-60%", "revise", "medium"),
        ("11", "Plan Approval mode", "approved", "high"),
        ("12", "Known limitations list", "approved", "high"),
        ("13", "Best use cases (4 categories)", "approved", "high"),
        ("14", "Quality gates (hooks)", "approved", "high"),
        ("15", "Cleanup only through lead", "approved", "high"),
    ]
    for num, claim, status, conf in claims:
        status_display = "approved" if status == "approved" else "revise"
        claims_data.append([
            Paragraph(num, s["table_cell_center"]),
            Paragraph(claim, s["table_cell"]),
            Paragraph(status_display, s["table_cell_center"]),
            Paragraph(conf, s["table_cell_center"]),
        ])

    col_widths = [25, 290, 65, 55]
    claims_table = Table(claims_data, colWidths=col_widths, repeatRows=1)
    claims_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#dfe6e9")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT),
    ]))
    story.append(claims_table)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "<b>Итого: 14 approved, 1 revise. Ни одного rejected.</b>", s["body_bold"]
    ))
    story.append(Paragraph(
        "Тезис 10 (revise): 40-60% экономия корректна для model switching в целом, "
        "но требует уточнения что это общая стратегия, а не специфичная метрика agent teams.",
        s["small"],
    ))
    story.append(PageBreak())

    # ============================================================
    # 4. YOUTUBE SCRIPT OUTLINE
    # ============================================================
    story.append(Paragraph("4. YouTube Script Outline", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Структура видео (~9–10 минут), подготовлена script-architect.", s["body"]
    ))

    outline_data = [
        [
            Paragraph("<b>Таймкод</b>", s["table_header"]),
            Paragraph("<b>Секция</b>", s["table_header"]),
            Paragraph("<b>Содержание</b>", s["table_header"]),
        ],
        [
            Paragraph("0:00–0:30", s["table_cell_center"]),
            Paragraph("HOOK", s["table_cell"]),
            Paragraph("Провокационное утверждение + тизер tmux с 6 агентами", s["table_cell"]),
        ],
        [
            Paragraph("0:30–1:30", s["table_cell_center"]),
            Paragraph("ПОЧЕМУ СЕЙЧАС", s["table_cell"]),
            Paragraph("Переход от single-agent к multi-agent, Anthropic первый", s["table_cell"]),
        ],
        [
            Paragraph("1:30–3:30", s["table_cell_center"]),
            Paragraph("ЧТО ТАКОЕ", s["table_cell"]),
            Paragraph("Архитектура, 4 компонента, отличие от subagents", s["table_cell"]),
        ],
        [
            Paragraph("3:30–6:30", s["table_cell_center"]),
            Paragraph("КАК РАБОТАЕТ", s["table_cell"]),
            Paragraph("Настройка, запуск, параллельная работа, зависимости и handoff", s["table_cell"]),
        ],
        [
            Paragraph("6:30–8:30", s["table_cell_center"]),
            Paragraph("PROOF", s["table_cell"]),
            Paragraph("Демонстрация артефактов, side-by-side до/после", s["table_cell"]),
        ],
        [
            Paragraph("8:30–9:30", s["table_cell_center"]),
            Paragraph("ИТОГ + CTA", s["table_cell"]),
            Paragraph("Shift к AI-командам, потенциал, вопрос зрителям", s["table_cell"]),
        ],
    ]
    outline_table = Table(outline_data, colWidths=[70, 100, 265], repeatRows=1)
    outline_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#dfe6e9")),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT),
    ]))
    story.append(outline_table)
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        '<b>Выбранный hook:</b> "Anthropic только что выпустил фичу, которую я не ожидал увидеть ещё минимум год."',
        s["body"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ============================================================
    # 5. КЛЮЧЕВЫЕ ВЫДЕРЖКИ ИЗ СКРИПТА
    # ============================================================
    story.append(Paragraph("5. Ключевые выдержки из скрипта", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "Полный скрипт доступен в video-script.md. Ниже — ключевые фрагменты.", s["body"]
    ))

    story.append(Paragraph("HOOK [0:00–0:30]", s["h2"]))
    story.append(Paragraph(
        "Anthropic только что выпустил фичу, которую я не ожидал увидеть ещё минимум год. "
        "Они превратили Claude Code из одиночного AI-ассистента — в оркестратор целой команды агентов. "
        "Каждый — со своей ролью. Каждый — со своим контекстом. И они реально общаются друг с другом.",
        s["body"],
    ))

    story.append(Paragraph("ПОЧЕМУ СЕЙЧАС [0:30–1:30]", s["h2"]))
    story.append(Paragraph(
        "Agent Teams меняют парадигму. Вместо одного агента ты запускаешь команду. "
        "Один ищет информацию. Другой проверяет факты. Третий пишет сценарий. "
        "И всё это — параллельно. В одном терминале. Без твоего вмешательства на каждом шаге. "
        "Ни Cursor, ни Copilot пока не предложили ничего подобного.",
        s["body"],
    ))

    story.append(Paragraph("ИТОГ [8:30–9:30]", s["h2"]))
    story.append(Paragraph(
        "Один человек. Команда AI-агентов. Результат за минуты. "
        "Шесть агентов, один запуск — материал для целого видео за несколько минут.",
        s["body"],
    ))
    story.append(Spacer(1, 4 * mm))

    # ============================================================
    # 6. АРХИТЕКТУРА AGENT TEAMS
    # ============================================================
    story.append(Paragraph("6. Архитектура Agent Teams", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Четыре компонента системы:</b>", s["body_bold"]))
    components = [
        ("<b>Team Lead</b> — главная сессия, создаёт команду, координирует работу, "
         "фиксирован на весь lifetime"),
        ("<b>Teammates</b> — отдельные Claude Code instances со своим context window, "
         "загружают проектный контекст"),
        ("<b>Task List</b> — общий список задач с зависимостями, тремя состояниями и file locking"),
        ("<b>Mailbox</b> — система обмена сообщениями (message + broadcast) с автодоставкой"),
    ]
    for c in components:
        story.append(Paragraph(f"• {c}", s["bullet"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Настройка:</b>", s["body_bold"]))
    story.append(Paragraph(
        'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS = "1" в settings.json',
        s["code"],
    ))
    story.append(Paragraph(
        'teammateMode = "tmux" (или "auto", "iterm2")',
        s["code"],
    ))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Workflow демо-проекта:</b>", s["body_bold"]))
    workflow_steps = [
        "1. showrunner получает задачу и составляет план",
        "2. web-researcher и visual-director стартуют параллельно",
        "3. fact-checker проверяет тезисы после завершения research",
        "4. script-architect строит сценарий на проверенных фактах",
        "5. pdf-producer собирает итоговый отчёт",
    ]
    for step in workflow_steps:
        story.append(Paragraph(step, s["body"]))
    story.append(PageBreak())

    # ============================================================
    # 7. ИЗВЕСТНЫЕ БАГИ И РИСКИ
    # ============================================================
    story.append(Paragraph("7. Известные баги и риски", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Ограничения (из документации):</b>", s["body_bold"]))
    limitations = [
        "Нет session resumption для in-process teammates",
        "Одна команда на сессию",
        "Нет вложенных команд (nested teams)",
        "Split panes только tmux / iTerm2",
        "Lead фиксирован на весь lifetime",
        "Permissions задаются при spawn",
    ]
    for lim in limitations:
        story.append(Paragraph(f"• {lim}", s["bullet"]))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Известные баги (GitHub Issues):</b>", s["body_bold"]))
    bugs_data = [
        [
            Paragraph("<b>Issue</b>", s["table_header"]),
            Paragraph("<b>Описание</b>", s["table_header"]),
        ],
        [
            Paragraph("#24292", s["table_cell_center"]),
            Paragraph('teammateMode "tmux" может не триггерить iTerm2 split panes', s["table_cell"]),
        ],
        [
            Paragraph("#23615", s["table_cell_center"]),
            Paragraph("Agent teams spawn в новом tmux window вместо split pane", s["table_cell"]),
        ],
        [
            Paragraph("#24771", s["table_cell_center"]),
            Paragraph("Split panes открываются, но teammates disconnected", s["table_cell"]),
        ],
        [
            Paragraph("#24385", s["table_cell_center"]),
            Paragraph("iTerm2 panes не закрываются при shutdown", s["table_cell"]),
        ],
    ]
    bugs_table = Table(bugs_data, colWidths=[70, 365], repeatRows=1)
    bugs_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#d63031")),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#ffeaea")]),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#dfe6e9")),
    ]))
    story.append(bugs_table)
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Риски для демо:</b>", s["body_bold"]))
    risks = [
        "Split pane mode имеет известные баги — может потребоваться fallback на in-process",
        "Cleanup должен запускаться только через lead",
        "При resumption in-process teammates не восстанавливаются",
    ]
    for r in risks:
        story.append(Paragraph(f"• {r}", s["bullet"]))
    story.append(Spacer(1, 6 * mm))

    # ============================================================
    # 8. ИСТОЧНИКИ
    # ============================================================
    story.append(Paragraph("8. Источники", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("<b>Первичные (официальные):</b>", s["body_bold"]))
    primary = [
        "Официальная документация Agent Teams — code.claude.com/docs/en/agent-teams",
        "Стоимость и токены — code.claude.com/docs/en/costs",
        "Subagents (для сравнения) — code.claude.com/docs/en/sub-agents",
        "Case study: C compiler — anthropic.com/engineering/building-c-compiler",
    ]
    for p in primary:
        story.append(Paragraph(f"• {p}", s["bullet"]))

    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Вторичные (сообщество):</b>", s["body_bold"]))
    secondary = [
        "Daniel Avila — Medium: Agent Teams in Claude Code",
        "Cobus Greyling — Medium: Claude Code Agent Teams",
        "Addy Osmani — Claude Code Swarms",
        "alexop.dev — From Tasks to Swarms",
        "paddo.dev — Hidden Multi-Agent System",
        "Turing College — Agent Teams Explained",
        "SitePoint — Anthropic Claude Code Agent Teams",
        "Claudefast — Agent Teams Guide",
        "Cuttlesoft — macOS Setup Guide",
    ]
    for sec in secondary:
        story.append(Paragraph(f"• {sec}", s["bullet"]))

    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "Отчёт собран pdf-producer на основе артефактов команды Agent Teams. "
        "Все ключевые тезисы верифицированы fact-checker с высоким уровнем доверия.",
        s["small"],
    ))
    story.append(Paragraph(
        "Статус: FINAL  |  14/15 approved  |  6 агентов  |  12+ источников",
        s["small"],
    ))

    # ============================================================
    # BUILD
    # ============================================================
    doc.build(
        story,
        onFirstPage=cover_page,
        onLaterPages=normal_page,
    )
    print(f"PDF generated: {OUTPUT_PDF}")


if __name__ == "__main__":
    build_pdf()
