# -*- coding: utf-8 -*-
import hashlib
import json
import logging
from datetime import datetime, time, timedelta

import babel.dates
import pytz
import requests

from weblgx import _, api, fields, models
from weblgx.exceptions import UserError

_logger = logging.getLogger(__name__)

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
# Ordre de tentative : V4 flash puis alias historique.
DEEPSEEK_MODELS = ("deepseek-v4-flash", "deepseek-chat")
HISTORY_MAX = 15
MAX_RETRIES = 2
GENERATION_HOURS = [(str(hour), f"{hour:02d}:00") for hour in range(24)]


class WebsiteAstuce(models.Model):
    _name = "website.astuce"
    _description = "Astuce du jour"
    _order = "sequence, id"

    name = fields.Char(
        string="Nom",
        required=True,
        default="Astuce du jour",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    website_id = fields.Many2one(
        "website",
        string="Site web",
        required=True,
        ondelete="cascade",
        index=True,
        default=lambda self: self.env["website"].get_current_website(),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Société",
        related="website_id.company_id",
        store=True,
        readonly=True,
    )
    prompt = fields.Text(
        string="Prompt",
        required=True,
        default=(
            "Peux-tu me fournir une anecdote courte et originale "
            "sur la ville d'Hondschoote ?"
        ),
        help="Texte envoyé à DeepSeek pour générer l'astuce.",
    )
    frequency = fields.Selection(
        [
            ("daily", "Une fois par jour"),
            ("weekly", "Une fois par semaine"),
        ],
        string="Fréquence de renouvellement",
        default="daily",
        required=True,
    )
    generation_hour = fields.Selection(
        selection=GENERATION_HOURS,
        string="Heure de génération",
        default="0",
        required=True,
        help=(
            "Heure locale de la société du site à laquelle l'astuce est renouvelée. "
            "Le planificateur contrôle ce créneau toutes les 15 minutes. "
            "Pour une astuce basée sur la date du jour, 00:00 aligne le texte "
            "sur le changement de jour, au lieu d'attendre 24 h après la génération précédente."
        ),
    )
    next_generation_label = fields.Char(
        string="Prochaine génération",
        compute="_compute_next_generation_label",
    )
    content = fields.Text(
        string="Contenu actuel",
        readonly=True,
        help="Dernière astuce générée par DeepSeek.",
    )
    last_generated = fields.Datetime(
        string="Dernière génération",
        readonly=True,
    )
    last_error = fields.Text(
        string="Dernière erreur",
        readonly=True,
    )
    history_json = fields.Text(
        string="Historique (JSON)",
        readonly=True,
        help="Astuces récentes utilisées pour éviter les doublons.",
    )

    def _get_history(self):
        self.ensure_one()
        if not self.history_json:
            return []
        try:
            data = json.loads(self.history_json)
            return data if isinstance(data, list) else []
        except (TypeError, ValueError, json.JSONDecodeError):
            return []

    def _normalize_tip(self, text):
        return " ".join((text or "").lower().split())

    def _tip_fingerprint(self, text):
        return hashlib.sha256(self._normalize_tip(text).encode("utf-8")).hexdigest()

    def _is_duplicate(self, text, history):
        tip = self._normalize_tip(text)
        if not tip:
            return True
        fingerprints = {self._tip_fingerprint(h) for h in history}
        if self._tip_fingerprint(text) in fingerprints:
            return True
        # Similarité grossière : même début significatif
        for prev in history:
            prev_n = self._normalize_tip(prev)
            if tip[:80] and prev_n[:80] and tip[:80] == prev_n[:80]:
                return True
        return False

    def _local_timezone(self):
        """Fuseau de la société du site, puis celui du contexte."""
        self.ensure_one()
        company = self.website_id.company_id
        tz_name = company.partner_id.tz if company and company.partner_id else False
        tz_name = tz_name or self.env.context.get("tz") or self.env.user.tz or "UTC"
        try:
            return pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            return pytz.UTC

    def _as_local(self, dt_naive_utc):
        self.ensure_one()
        if not dt_naive_utc:
            return False
        if getattr(dt_naive_utc, "tzinfo", None):
            dt_naive_utc = dt_naive_utc.astimezone(pytz.UTC).replace(tzinfo=None)
        return pytz.UTC.localize(dt_naive_utc).astimezone(self._local_timezone())

    def _generation_hour_int(self):
        self.ensure_one()
        try:
            hour = int(self.generation_hour)
        except (TypeError, ValueError):
            hour = 0
        return min(23, max(0, hour))

    def _localize_slot(self, day, hour):
        """Créneau local à `hour`:00 le jour `day` (gère les transitions d'heure d'été)."""
        self.ensure_one()
        tz = self._local_timezone()
        naive = datetime.combine(day, time(hour, 0))
        try:
            return tz.localize(naive, is_dst=None)
        except pytz.AmbiguousTimeError:
            return tz.localize(naive, is_dst=False)
        except pytz.NonExistentTimeError:
            return tz.localize(naive + timedelta(hours=1), is_dst=None)

    def _daily_period_start(self, moment_local):
        """Début de la période journalière qui contient `moment_local`."""
        self.ensure_one()
        hour = self._generation_hour_int()
        start = self._localize_slot(moment_local.date(), hour)
        if moment_local < start:
            start = self._localize_slot(moment_local.date() - timedelta(days=1), hour)
        return start

    def _next_generation_local(self):
        """Prochain créneau local. Dans le passé si le renouvellement est déjà dû."""
        self.ensure_one()
        now_local = self._as_local(fields.Datetime.now())
        if not self.last_generated:
            return now_local
        last_local = self._as_local(self.last_generated)
        hour = self._generation_hour_int()
        if self.frequency == "weekly":
            return self._localize_slot(last_local.date() + timedelta(days=7), hour)
        current_start = self._daily_period_start(now_local)
        if last_local < current_start:
            return current_start
        return self._localize_slot(current_start.date() + timedelta(days=1), hour)

    def _is_due(self):
        self.ensure_one()
        if not self.last_generated:
            return True
        now_local = self._as_local(fields.Datetime.now())
        return now_local >= self._next_generation_local()

    @api.depends(
        "last_generated",
        "frequency",
        "generation_hour",
        "website_id.company_id.partner_id.tz",
    )
    def _compute_next_generation_label(self):
        for astuce in self:
            if not astuce.last_generated:
                astuce.next_generation_label = _(
                    "Dès le prochain passage du planificateur"
                )
                continue
            slot = astuce._next_generation_local()
            now_local = astuce._as_local(fields.Datetime.now())
            if slot <= now_local:
                astuce.next_generation_label = _(
                    "Dès le prochain passage du planificateur"
                )
                continue
            tz_name = getattr(slot.tzinfo, "zone", None) or "UTC"
            try:
                label = babel.dates.format_datetime(
                    slot, format="EEEE d MMMM y 'à' HH:mm", locale="fr_FR"
                )
            except Exception:
                label = slot.strftime("%d/%m/%Y %H:%M")
            astuce.next_generation_label = f"{label} ({tz_name})"

    def _today_label(self):
        """Date du jour dans le fuseau de la société du site."""
        self.ensure_one()
        today = self._as_local(fields.Datetime.now()).date()
        try:
            label = babel.dates.format_date(
                today, format="EEEE d MMMM y", locale="fr_FR"
            )
        except Exception:
            label = today.isoformat()
        return today, label

    def _build_messages(self, history):
        self.ensure_one()
        today, today_label = self._today_label()
        system = (
            "Tu es un assistant éditorial pour un site web. "
            f"La date du jour est le {today_label} ({today.isoformat()}). "
            "C'est la seule date valide. N'utilise jamais une date issue "
            "de tes connaissances ou de tes données d'entraînement. "
            "Si on te demande la date, le jour, le mois ou l'année, "
            "réponds avec cette date-là. "
            "Réponds uniquement avec le texte de l'astuce ou de l'anecdote, "
            "en français, en 2 à 5 phrases complètes. "
            "Termine toujours par une phrase entière (point final). "
            "Pas de titre, pas de liste, pas de markdown, pas d'introduction."
        )
        if history:
            recent = "\n".join(f"- {h}" for h in history[-HISTORY_MAX:])
            system += (
                "\n\nN'écris PAS une variante des textes suivants déjà publiés :\n"
                f"{recent}"
            )
        user = (
            f"Date du jour imposée : {today_label} ({today.isoformat()}). "
            "Utilise exclusivement cette date.\n\n"
            f"{self.prompt.strip()}"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _deepseek_post(self, api_key, payload):
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code == 402:
            raise UserError(
                _(
                    "Solde DeepSeek insuffisant. "
                    "Rechargez le compte sur platform.deepseek.com."
                )
            )
        return response

    def _call_deepseek(self, api_key, messages):
        last_error_text = ""
        for model_name in DEEPSEEK_MODELS:
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": 0.95,
                "max_tokens": 1200,
                # Sans cela, le mode thinking V4 peut consommer le budget
                # et tronquer le texte affiché.
                "thinking": {"type": "disabled"},
            }
            response = self._deepseek_post(api_key, payload)
            if response.status_code >= 400:
                last_error_text = response.text[:500]
                if response.status_code == 400 and "thinking" in last_error_text.lower():
                    payload = {k: v for k, v in payload.items() if k != "thinking"}
                    response = self._deepseek_post(api_key, payload)
                    if response.status_code >= 400:
                        last_error_text = response.text[:500]
                if response.status_code >= 400:
                    if response.status_code in (400, 404) and model_name != DEEPSEEK_MODELS[-1]:
                        continue
                    raise UserError(
                        _("Erreur DeepSeek HTTP %(code)s : %(body)s")
                        % {"code": response.status_code, "body": last_error_text}
                    )
            data = response.json()
            try:
                choice = data["choices"][0]
                text = (choice.get("message", {}).get("content") or "").strip()
                if choice.get("finish_reason") == "length":
                    _logger.warning(
                        "DeepSeek truncated response (finish_reason=length) for model %s",
                        model_name,
                    )
                return text
            except (KeyError, IndexError, TypeError) as exc:
                raise UserError(
                    _("Réponse DeepSeek inattendue : %s") % (response.text[:500],)
                ) from exc
        raise UserError(
            _("Erreur DeepSeek : aucun modèle compatible. %s") % last_error_text
        )

    def _fetch_from_deepseek(self, force=False):
        """Génère une nouvelle astuce via DeepSeek (évite les doublons récents)."""
        for astuce in self:
            if not force and not astuce._is_due():
                continue
            website = astuce.website_id
            api_key = (website.deepseek_api_key or "").strip()
            if not api_key:
                msg = _("Aucune clé API DeepSeek configurée pour le site « %s ».") % (
                    website.name,
                )
                astuce.last_error = msg
                _logger.warning("website.astuce %s: %s", astuce.id, msg)
                continue
            if not (astuce.prompt or "").strip():
                astuce.last_error = _("Le prompt est vide.")
                continue

            history = astuce._get_history()
            tip = None
            last_exc = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    tip = astuce._call_deepseek(
                        api_key, astuce._build_messages(history)
                    )
                except Exception as exc:
                    last_exc = exc
                    _logger.exception(
                        "DeepSeek failed for website.astuce %s (attempt %s)",
                        astuce.id,
                        attempt + 1,
                    )
                    tip = None
                    continue
                if tip and not astuce._is_duplicate(tip, history):
                    break
                tip = None

            if not tip:
                msg = str(last_exc) if last_exc else _(
                    "Impossible d'obtenir une astuce différente des précédentes."
                )
                astuce.last_error = msg
                continue

            history.append(tip)
            history = history[-HISTORY_MAX:]
            astuce.write(
                {
                    "content": tip,
                    "last_generated": fields.Datetime.now(),
                    "last_error": False,
                    "history_json": json.dumps(history, ensure_ascii=False),
                }
            )
        return True

    def action_refresh_now(self):
        self._fetch_from_deepseek(force=True)
        return True

    @api.model
    def _cron_refresh_astuces(self):
        due = self.search([("active", "=", True)]).filtered(lambda a: a._is_due())
        if due:
            due._fetch_from_deepseek(force=True)

    @api.model
    def get_public_payload(self, astuce_id=None, website=None):
        """Données publiques pour le building block (sans clé API)."""
        website = website or self.env["website"].get_current_website()
        domain = [
            ("active", "=", True),
            ("website_id", "=", website.id),
        ]
        if astuce_id:
            domain.append(("id", "=", int(astuce_id)))
        astuce = self.sudo().search(domain, limit=1, order="sequence, id")
        if not astuce:
            return {
                "id": False,
                "name": _("Astuce du jour"),
                "content": "",
                "empty": True,
            }
        return {
            "id": astuce.id,
            "name": astuce.name,
            "content": astuce.content or "",
            "empty": not bool(astuce.content),
            "last_generated": fields.Datetime.to_string(astuce.last_generated)
            if astuce.last_generated
            else False,
        }
