from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

_STYLES = getSampleStyleSheet()

_TITLE_STYLE = ParagraphStyle(
    "PlanTitle",
    parent=_STYLES["Title"],
    textColor=colors.HexColor("#0e1f19"),
)

_HEADING_STYLE = ParagraphStyle(
    "SectionHeading",
    parent=_STYLES["Heading2"],
    textColor=colors.HexColor("#218f57"),
    spaceBefore=14,
    spaceAfter=6,
)

_SUBHEADING_STYLE = ParagraphStyle(
    "SubHeading",
    parent=_STYLES["Heading3"],
    textColor=colors.HexColor("#0e1f19"),
    spaceBefore=10,
    spaceAfter=4,
)

_BODY_STYLE = ParagraphStyle(
    "Body",
    parent=_STYLES["BodyText"],
    textColor=colors.HexColor("#1a1a1a"),
)

_MEAL_HEADER_STYLE = ParagraphStyle(
    "MealHeader",
    parent=_BODY_STYLE,
    fontName="Helvetica-Bold",
)

_TOTAL_STYLE = ParagraphStyle(
    "Total",
    parent=_BODY_STYLE,
    fontName="Helvetica-Bold",
)

_DISCLAIMER_STYLE = ParagraphStyle(
    "Disclaimer",
    parent=_BODY_STYLE,
    textColor=colors.HexColor("#665620"),
    fontSize=9,
)

_TABLE_HEADER_BG = colors.HexColor("#0e1f19")
_TABLE_GRID_COLOR = colors.HexColor("#e1e8e4")


def _table_style(header_color: colors.Color) -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, _TABLE_GRID_COLOR),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def _macro_table(targets: dict[str, Any]) -> Table:
    data = [
        ["Calories", "Protein", "Carbohydrates", "Fat"],
        [
            f'{targets.get("calories", 0):,.0f}',
            f'{targets.get("protein_g", 0):,.0f} g',
            f'{targets.get("carbs_g", 0):,.0f} g',
            f'{targets.get("fat_g", 0):,.0f} g',
        ],
    ]

    table = Table(data, hAlign="LEFT")
    table.setStyle(_table_style(_TABLE_HEADER_BG))

    return table


def _bullet_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, _BODY_STYLE)) for item in items],
        bulletType="bullet",
        leftIndent=14,
    )


def _numbered_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, _BODY_STYLE)) for item in items],
        bulletType="1",
        leftIndent=14,
    )


def build_meal_plan_pdf(plan: dict[str, Any]) -> bytes:
    """
    Render a meal plan dictionary into a formatted PDF and return its
    raw bytes.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        title=plan.get("plan_title", "Your FirstRep Meal Plan"),
    )

    story: list[Any] = [
        Paragraph(
            plan.get("plan_title", "Your FirstRep Meal Plan"),
            _TITLE_STYLE,
        ),
    ]

    summary = plan.get("summary", "")

    if summary:
        story.append(Paragraph(summary, _BODY_STYLE))

    story.append(Spacer(1, 12))

    story.append(Paragraph("Estimated daily targets", _HEADING_STYLE))
    story.append(_macro_table(plan.get("estimated_daily_targets", {})))

    story.append(Paragraph("Daily meal plan", _HEADING_STYLE))

    for day in plan.get("days", []):
        day_number = day.get("day", "?")

        story.append(Paragraph(f"Day {day_number}", _SUBHEADING_STYLE))
        story.append(_macro_table(day.get("daily_totals", {})))

        for meal in day.get("meals", []):
            story.append(Spacer(1, 6))

            meal_header = (
                f'{meal.get("meal_type", "Meal")}: '
                f'{meal.get("name", "Unnamed meal")}'
            )

            story.append(Paragraph(meal_header, _MEAL_HEADER_STYLE))

            macro_line = (
                f'{meal.get("calories", 0)} calories &middot; '
                f'{meal.get("protein_g", 0)} g protein &middot; '
                f'{meal.get("carbs_g", 0)} g carbs &middot; '
                f'{meal.get("fat_g", 0)} g fat'
            )

            story.append(Paragraph(macro_line, _BODY_STYLE))

            ingredients = meal.get("ingredients", [])

            if ingredients:
                story.append(Paragraph("Ingredients:", _BODY_STYLE))
                story.append(_bullet_list(ingredients))

            instructions = meal.get("instructions", [])

            if instructions:
                story.append(Paragraph("Instructions:", _BODY_STYLE))
                story.append(_numbered_list(instructions))

    story.append(Paragraph("Grocery list", _HEADING_STYLE))

    for category in plan.get("grocery_list", []):
        category_name = category.get("category", "Other")

        story.append(Paragraph(category_name, _SUBHEADING_STYLE))

        rows = [["Item", "Quantity", "Estimated price"]]

        for item in category.get("items", []):
            rows.append(
                [
                    item.get("name", ""),
                    item.get("quantity", ""),
                    f'${item.get("estimated_price", 0):.2f}',
                ]
            )

        if len(rows) > 1:
            table = Table(rows, hAlign="LEFT")
            table.setStyle(
                _table_style(colors.HexColor("#218f57"))
            )

            story.append(table)
            story.append(Spacer(1, 8))

    total = plan.get("estimated_grocery_total", 0)

    story.append(
        Paragraph(
            f"Estimated grocery total: ${total:,.2f}",
            _TOTAL_STYLE,
        )
    )

    prep_tips = plan.get("prep_tips", [])

    if prep_tips:
        story.append(Paragraph("Meal-prep tips", _HEADING_STYLE))
        story.append(_bullet_list(prep_tips))

    disclaimer = plan.get(
        "disclaimer",
        (
            "This plan is general educational information and is not "
            "medical advice."
        ),
    )

    story.append(Spacer(1, 12))
    story.append(Paragraph(disclaimer, _DISCLAIMER_STYLE))

    document.build(story)

    return buffer.getvalue()
