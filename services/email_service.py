import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any


def build_meal_plan_email_html(plan: dict[str, Any]) -> str:
    """
    Build an organized HTML summary of the meal plan for the email body.
    The full plan (all days, ingredients, and instructions) is sent as
    the attached PDF rather than inlined here.
    """

    targets = plan.get("estimated_daily_targets", {})
    day_count = len(plan.get("days", []))
    total = plan.get("estimated_grocery_total", 0)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="color-scheme" content="light dark">
        <meta name="supported-color-schemes" content="light dark">
        <style>
            @media (prefers-color-scheme: dark) {{
                .hero-box, .hero-box * {{ color: #ffffff !important; }}
                .hero-box {{
                    background: linear-gradient(135deg, #0e1f19, #1a5b3d) !important;
                }}
            }}
        </style>
    </head>
    <body>
    <div style="font-family: Arial, sans-serif; color: white;">
        <div class="hero-box" style="background: linear-gradient(135deg, #0e1f19, #1a5b3d);
                    color: #ffffff !important; padding: 24px; border-radius: 16px;">
            <div style="font-size: 12px; letter-spacing: 1.5px;
                        text-transform: uppercase; color: #ffffff !important;">
                FirstRep Nutrition
            </div>
            <h1 style="margin: 8px 0; font-size: 28px; color: #ffffff !important;">
                {plan.get("plan_title", "Your FirstRep Meal Plan")}
            </h1>
            <p style="color: #ffffff !important; margin: 0;">
                {plan.get("summary", "")}
            </p>
        </div>

        <h2 style="color: #218f57; margin-top: 24px;">
            Estimated daily targets
        </h2>
        <table style="border-collapse: collapse; width: 100%;">
            <tr style="background: #0e1f19; color: white;">
                <th style="padding: 8px; text-align: left;">Calories</th>
                <th style="padding: 8px; text-align: left;">Protein</th>
                <th style="padding: 8px; text-align: left;">Carbs</th>
                <th style="padding: 8px; text-align: left;">Fat</th>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #e1e8e4;">
                    {targets.get("calories", 0):,.0f}
                </td>
                <td style="padding: 8px; border: 1px solid #e1e8e4;">
                    {targets.get("protein_g", 0):,.0f} g
                </td>
                <td style="padding: 8px; border: 1px solid #e1e8e4;">
                    {targets.get("carbs_g", 0):,.0f} g
                </td>
                <td style="padding: 8px; border: 1px solid #e1e8e4;">
                    {targets.get("fat_g", 0):,.0f} g
                </td>
            </tr>
        </table>

        <p style="margin-top: 20px;">
            This plan covers <strong>{day_count} day(s)</strong> with an
            estimated grocery total of <strong>${total:,.2f}</strong>.
        </p>

        <p>
            Your complete meal-by-meal plan, ingredients, instructions,
            and grocery list are attached to this email as a
            <strong>PDF</strong>. Open the attachment to download and
            save it.
        </p>

        <p style="color: #888; font-size: 12px; margin-top: 24px;">
            This plan is general educational information and is not
            medical advice.
        </p>
    </div>
    </body>
    </html>
    """


def send_meal_plan_email(
    sender_email: str,
    sender_password: str,
    to_email: str,
    plan: dict[str, Any],
    pdf_bytes: bytes,
) -> None:
    """
    Email the meal plan as an organized HTML summary with the full plan
    attached as a downloadable PDF, sent through Gmail's SMTP server.
    """

    message = MIMEMultipart()
    message["Subject"] = plan.get("plan_title", "Your FirstRep Meal Plan")
    message["From"] = sender_email
    message["To"] = to_email

    message.attach(MIMEText(build_meal_plan_email_html(plan), "html"))

    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename="firstrep_meal_plan.pdf",
    )
    message.attach(attachment)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_string())
