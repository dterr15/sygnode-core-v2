"""Mailgun service — send RFQ emails to suppliers."""

import httpx
from app.settings import settings


class MailgunService:
    def __init__(self):
        self.api_key = settings.mailgun_api_key
        self.domain = settings.mailgun_domain
        self.from_email = settings.mailgun_from_email
        self.base_url = f"https://api.mailgun.net/v3/{self.domain}"

    async def send_rfq_email(
        self,
        to_email: str,
        supplier_name: str,
        rfq_title: str,
        items_html: str,
        reply_to: str = "rfq@sygnode.cl",
    ) -> dict:
        """Send RFQ solicitation email to a supplier."""
        subject = f"Solicitud de Cotización: {rfq_title}"
        html_body = f"""
        <p>Estimado/a {supplier_name},</p>
        <p>Junto con saludar, le solicitamos cotización para los siguientes ítems:</p>
        {items_html}
        <p>Favor responder a este correo con su cotización.</p>
        <p>Saludos cordiales,<br>Equipo de Adquisiciones</p>
        """

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                auth=("api", self.api_key),
                data={
                    "from": self.from_email,
                    "to": to_email,
                    "subject": subject,
                    "html": html_body,
                    "h:Reply-To": reply_to,
                },
            )
            response.raise_for_status()
            return response.json()


mailgun_service = MailgunService()
