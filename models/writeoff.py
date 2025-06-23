# amanat/models/writeoff.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from datetime import datetime, timedelta, date
import calendar
import pytz

_logger = logging.getLogger(__name__)


# --- Вспомогательные функции ---
def parse_date_from_string(date_str):
    """
    Парсит дату из строки формата 'dd.mm.yyyy'.
    """
    if not isinstance(date_str, str):
        _logger.warning("parse_date_from_string: не строка: %s", date_str)
        return None
    parts = date_str.split(".")
    if len(parts) != 3:
        _logger.warning("parse_date_from_string: неверный формат: %s", date_str)
        return None
    try:
        day, month, year = map(int, parts)
        return date(year, month, day)
    except ValueError:
        _logger.warning(
            "parse_date_from_string: не удалось преобразовать части в int: %s", date_str
        )
        return None


def days_between(d1, d2):
    """Вычисляет целое число дней между двумя датами."""
    if not (isinstance(d1, date) and isinstance(d2, date)):
        _logger.warning("days_between: некорректные даты %s, %s", d1, d2)
        return 0
    return (d2 - d1).days


def get_period_days(period_key, start_date):
    """Количество дней в периоде от start_date"""
    if not isinstance(start_date, date):
        return 1
    # Учёт ключей selection поля
    if period_key == "calendar_day":
        return 1
    if period_key == "work_day":
        return 1
    if period_key == "calendar_month":
        year, month = start_date.year, start_date.month
        return calendar.monthrange(year, month)[1]
    if period_key == "calendar_year":
        return 366 if calendar.isleap(start_date.year) else 365
    return 1


def get_month_days(dt):
    """Число дней в месяце даты dt"""
    return calendar.monthrange(dt.year, dt.month)[1]


class WriteOff(models.Model):
    _name = "amanat.writeoff"
    _inherit = ["amanat.base.model", "mail.thread", "mail.activity.mixin"]
    _description = "Списания"

    # Пользовательское поле-идентификатор «Id Списания» (вместо name)
    # Если хотите назвать его name, переименуйте соответственно.
    id_spisaniya = fields.Char(
        string="Id Списания",
        tracking=True,
        default=lambda self: self.env["ir.sequence"].next_by_code(
            "amanat.writeoff.sequence"
        ),
    )

    date = fields.Date(
        string="Дата",
        tracking=True,
        default=fields.Date.today,
    )
    amount = fields.Float(string="Сумма", tracking=True)

    sender_id = fields.Many2one(
        "amanat.contragent",
        string="Отправитель",
        tracking=True,
    )
    sender_payer_id = fields.Many2one(
        "amanat.payer",
        string="Плательщик отправителя",
        tracking=True,
        domain="[('contragents_ids', 'in', sender_id)]",
    )
    sender_wallet_id = fields.Many2one(
        "amanat.wallet", string="Кошелек отправителя", tracking=True
    )

    @api.onchange("sender_id")
    def _onchange_sender_id(self):
        if self.sender_id:
            payer = self.env["amanat.payer"].search(
                [("contragents_ids", "in", self.sender_id.id)], limit=1
            )
            self.sender_payer_id = payer.id if payer else False
        else:
            self.sender_payer_id = False

    # Ссылка на модель "amanat.money" (Контейнер)
    money_id = fields.Many2one(
        "amanat.money",
        string="Контейнер",
        tracking=True,
        ondelete="cascade",
    )

    # Ссылка на модель "amanat.investment"
    investment_ids = fields.Many2many(
        "amanat.investment",
        "amanat_investment_writeoff_rel",
        "writeoff_id",
        "investment_id",
        string="Инвестиции",
        tracking=True,
    )

    # Списание инвестиции. Используется для автоматизации
    writeoff_investment = fields.Boolean(
        string="Списание инвестиций",
        default=False,
        tracking=True,
    )

    @api.model
    def create(self, vals):
        run_automation = vals.get('writeoff_investment', False)
        rec = super().create(vals)

        # Автоматически обновляем состояние контейнера денег
        if rec.money_id:
            rec.money_id.update_state_based_on_remainder()

        if run_automation:
            try:
                rec.process_write_off()
                rec.create_transfer_after_writeoff()
                # Сбрасываем флаг до начисления процентов
                rec.write({"writeoff_investment": False})
                # Теперь запускаем cron: первичное списание уже не подлежит удалению
                rec.cron_accrue_interest()
            except Exception as e:
                _logger.error("Ошибка при автоматической обработке create: %s", e)
                raise

        return rec

    def write(self, vals):
        res = super().write(vals)

        # Автоматически обновляем состояние контейнера денег
        for rec in self:
            if rec.money_id:
                rec.money_id.update_state_based_on_remainder()

        run_automation = vals.get('writeoff_investment', False)

        for rec in self:
            if run_automation:
                try:
                    rec.process_write_off()
                    rec.create_transfer_after_writeoff()
                    rec.cron_accrue_interest()
                    # Сбрасываем флаг до начисления процентов
                    rec.write({"writeoff_investment": False})
                    # Теперь запускаем cron: первичное списание уже не подлежит удалению
                    rec.cron_accrue_interest()
                except Exception as e:
                    _logger.error("Ошибка при автоматической обработке write: %s", e)
                    raise

        return res

    @api.model
    def process_write_off(self):
        """
        Функция обрабатывает списание:
        - Привязывает подходящие контейнеры
        - Создает обратное списание на долговой контейнер
        """

        self.ensure_one()

        if not self.writeoff_investment:
            _logger.info(
                "process_write_off: writeoff_investment=False, пропуск выполнения"
            )
            return True

        investment = self.investment_ids
        if not investment:
            raise ValidationError("Не указана инвестиция")

        order = investment.orders[:1]
        if not order:
            raise ValidationError("Нет связанного ордера")

        money_records = order.money_ids
        if not money_records:
            raise ValidationError("Нет связанных контейнеров")

        valid_container = money_records.filtered(
            lambda m: not m.percent and not m.royalty and m.state != "debt"
        )[:1]
        if not valid_container:
            raise ValidationError("Нет подходящих контейнеров")
        
        debt_container = money_records.filtered(
            lambda m: not m.percent and not m.royalty and m.state == "debt"
        )[:1]
        if not debt_container:
            raise ValidationError("Нет подходящих долговых контейнеров")
        
        if self.amount < 0:
            raise ValidationError("Нельзя списать инвестицию с отрицательной суммой")
        
        # …после нахождения valid_container
        self.write({'money_id': valid_container.id})

        new_writeoff = self.create(
            {
                "amount": -self.amount,
                "date": self.date,
                "money_id": debt_container.id,
                "investment_ids": [(6, 0, [investment.id])],
                "writeoff_investment": False,
            }
        )

        _logger.info(f"Создался инвертированное списание: {new_writeoff}")

        return True

    def create_transfer_after_writeoff(self):
        """
        Создает запись в 'Перевод' (amanat.transfer) на основе данных списания и инвестиции.
        """
        self.ensure_one()

        # Если автоматизация не активирована, пропускаем
        if not self.writeoff_investment:
            _logger.info(
                "create_transfer_after_writeoff: writeoff_investment=False, пропуск выполнения"
            )
            return True

        if not self.sender_id or not self.sender_payer_id or not self.sender_wallet_id:
            _logger.error(
                "Отсутствуют данные отправителя: %s, %s, %s",
                self.sender_id,
                self.sender_payer_id,
                self.sender_wallet_id,
            )
            raise ValidationError("Отсутствуют данные отправителя")

        if not self.investment_ids:
            raise ValidationError("Нет связанной инвестиции")

        investment = self.investment_ids[:1]

        if (
            not investment.sender
            or not investment.payer_sender
            or not investment.currency
        ):
            raise ValidationError("Отсутствуют данные получателя или валюты")

        # Найти кошелек получателя с названием "Инвестиции"
        recipient_wallet = self.env["amanat.wallet"].search(
            [("name", "=", "Инвестиции")], limit=1
        )
        if not recipient_wallet:
            raise ValidationError("Кошелек 'Инвестиции' не найден")

        # Соответствие (маппинг) между между investment и transfer
        CURRENCY_MAP = {
            "RUB": "rub",
            "RUB_cash": "rub_cashe",
            "USD": "usd",
            "USD_cash": "usd_cashe",
            "USDT": "usdt",
            "EURO": "euro",
            "EURO_cash": "euro_cashe",
            "CNY": "cny",
            "CNY_cash": "cny_cashe",
            "AED": "aed",
            "AED_cash": "aed_cashe",
            "THB": "thb",
            "THB_cash": "thb_cashe",
        }
        transfer_currency = CURRENCY_MAP.get(investment.currency)
        if not transfer_currency:
            raise ValueError(f"Неизвестная валюта: {investment.currency}")

        transfer = self.env["amanat.transfer"].create(
            {
                "date": self.date,
                "currency": transfer_currency,
                "amount": self.amount,
                "sender_id": self.sender_id.id,
                "sender_payer_id": self.sender_payer_id.id,
                "sender_wallet_id": self.sender_wallet_id.id,
                "receiver_id": investment.sender.id,
                "receiver_payer_id": investment.payer_sender.id,
                "receiver_wallet_id": recipient_wallet.id,
                "create_order": True,
            }
        )

        _logger.info(f"Создался перевод на списание: {transfer}")

        return True

    @api.model
    def cron_accrue_interest(self):
        """
        Плановая задача: ежедневно начислять проценты и роялти по инвестициям.
        Создает записи списаний (amanat.writeoff).
        """
        _logger.info("=== Начало ежедневного начисления процентов и роялти ===")
        # Сегодня в контексте пользователя
        today = fields.Date.context_today(self)
        # Получаем текущее время по Москве
        moscow_tz = pytz.timezone('Europe/Moscow')
        now_utc = fields.Datetime.now(self)
        now_moscow = now_utc.astimezone(moscow_tz)
        if isinstance(today, str):
            today = datetime.strptime(today, "%Y-%m-%d").date()

        if now_moscow.hour < 20:
            _logger.info(
                "cron_accrue_interest: текущее время %s <20:00, считаем today = вчера",
                now_moscow
            )
            today = today - timedelta(days=1)
        else:
            _logger.info(
                "cron_accrue_interest: текущее время %s >=20:00, считаем today = %s",
                now_moscow, today
            )

        # Получаем все открытые инвестиции
        Investment = self.env["amanat.investment"]
        investments = Investment.search([("status", "=", "open")])
        WriteOff = self.env["amanat.writeoff"]

        for inv in investments:
            _logger.info("Обработка инвестиции ID: %s", inv.id)
            # Получаем дату начала
            start_date = None
            if isinstance(inv.date, date):
                start_date = inv.date
            elif isinstance(inv.date, str):
                try:
                    start_date = datetime.strptime(inv.date, "%Y-%m-%d").date()
                except ValueError:
                    start_date = parse_date_from_string(inv.date)
            if not start_date:
                _logger.warning(
                    "Инвестиция %s: не указана или неверен формат даты", inv.id
                )
                continue

            # Исходная сумма и процент
            principal_initial = inv.amount
            percent = inv.percent
            period = inv.period
            working_days_limit = inv.work_days
            order = inv.orders[:1]
            if not order or not percent or principal_initial <= 0:
                _logger.info(
                    "Инвестиция %s: пропущена из-за отсутствующих данных", inv.id
                )
                continue

            # Находим контейнеры
            money_recs = order.money_ids
            # Контейнеры для процентов
            cont_int_sender = money_recs.filtered(
                lambda m: m.percent and m.partner_id == inv.sender
            )
            cont_int_receiver = money_recs.filtered(
                lambda m: m.percent and m.partner_id == inv.receiver
            )
            if not cont_int_sender or not cont_int_receiver:
                _logger.warning("Инвестиция %s: нет контейнеров процентов", inv.id)
                continue
            # Контейнеры для роялти
            cont_royalty = money_recs.filtered(
                lambda m: m.royalty and m.wallet_id.name == "Инвестиции"
            )

            # Получаем текущее остаток и writeoff-записи
            principal_records = money_recs.filtered(
                lambda m: not m.percent
                and not m.royalty
                and m.wallet_id.name == "Инвестиции"
            )
            if not principal_records:
                _logger.warning("Инвестиция %s: нет основного контейнера", inv.id)
                continue
            p_rec = principal_records[0]

            # Дата первого начисления
            first_date = (p_rec.date or today) + timedelta(
                days=1
            )  # TODO: заменить date
            if first_date > today:
                continue

            # Собираем списания для удаления старых
            all_cont_ids = cont_int_sender.ids + cont_int_receiver.ids + cont_royalty.ids
            if all_cont_ids:
                old_wos = WriteOff.search([("money_id", "in", all_cont_ids)])
                if old_wos:
                    _logger.info(
                        "Инвестиция %s: удаляем %s старых списаний (по контейнерам %s)",
                        inv.id, len(old_wos), all_cont_ids
                    )
                    old_wos.unlink()
                else:
                    _logger.info("Старые списания не найден в all_cont_ids")

            # Начинаем цикл по дням
            day = first_date
            days_total = days_between(first_date, today)
            day_count = 0

            # 8) Подготовка для учёта досрочных списаний
            existing_wos = WriteOff.search(
                [("investment_ids", "in", inv.id), ("writeoff_investment", "=", False)],
                order="date asc"
            )
            def adjust_principal(day_cursor, init_p):
                p = init_p
                for w in existing_wos:
                    if w.date <= day_cursor:
                        p -= w.amount
                    else:
                        break
                return p

            # 9) Период для «годового» расчёта
            period_days = get_period_days(period, start_date)

            while day <= today and (
                period != "work_day" or day_count < working_days_limit
            ):
                # Пропуск выходных для рабочего дня
                if period == "work_day" and day.weekday() >= 5:
                    day += timedelta(days=1)
                    continue

                # TODO: учитывать досрочные списания: корректировать principal_initial по суммам writeoff до day
                # 11) Корректируем principal
                principal = adjust_principal(day, principal_initial)

                # Расчёт ежедневного процента
                daily_pct = percent
                if period == "calendar_month":
                    daily_pct /= get_month_days(day)
                elif period == "calendar_year":
                    daily_pct /= period_days

                amount_interest = principal * daily_pct
                # Создаём списания процентов отправителю и получателю
                if amount_interest:
                    writeoff1 = WriteOff.create(
                        {
                            "date": day,
                            "amount": amount_interest,
                            "money_id": cont_int_sender.id,
                            "investment_ids": [(6, 0, [inv.id])],
                            "writeoff_investment": False,
                        }
                    )
                    writeoff2 = WriteOff.create(
                        {
                            "date": day,
                            "amount": -amount_interest,
                            "money_id": cont_int_receiver.id,
                            "investment_ids": [(6, 0, [inv.id])],
                            "writeoff_investment": False,
                        }
                    )
                    _logger.info(f"Создалось 2 списания: {writeoff1} {writeoff2}")

                # Расчёт и создание роялти
                if inv.has_royalty:
                    for idx in range(1, 10):
                        recipient = getattr(inv, f"royalty_recipient_{idx}", False)
                        pct = getattr(inv, f"percent_{idx}", 0.0)
                        if recipient and pct:
                            amt_roy = principal * pct
                            cont = cont_royalty.filtered(
                                lambda m: m.partner_id.id == recipient.id
                            )
                            if cont:
                                write_off_royal = WriteOff.create(
                                    {
                                        "date": day,
                                        "amount": amt_roy,
                                        "money_id": cont.id,
                                        "investment_ids": [(6, 0, [inv.id])],
                                        "writeoff_investment": False,
                                    }
                                )
                                _logger.info(f"Создалось роялти списания: {write_off_royal}")

                day += timedelta(days=1)
                day_count += 1

            _logger.info("Инвестиция %s: начислено за %s дней", inv.id, days_total)

        _logger.info("=== Завершено ежедневное начисление процентов и роялти ===")

    def unlink(self):
        # Сохраняем ссылки на контейнеры денег перед удалением
        money_containers = self.mapped('money_id')
        
        result = super().unlink()
        
        # Автоматически обновляем состояние контейнеров денег
        for container in money_containers:
            if container.exists():
                container.update_state_based_on_remainder()
        
        return result
