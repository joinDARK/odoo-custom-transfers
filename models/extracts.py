from odoo import models, fields, api
from .base_model import AmanatBaseModel
import base64
import re
import logging
from odoo.exceptions import UserError
from datetime import datetime

_logger = logging.getLogger(__name__)

class AmanatExtracts(models.Model, AmanatBaseModel):
    _name = 'amanat.extracts'
    _inherit = ['amanat.base.model', "mail.thread", "mail.activity.mixin"]
    _description = 'extracts'
    _order = 'id desc'

    name = fields.Char(string='ID', tracking=True)

    vypiska_ids = fields.Many2many(
        'ir.attachment',
        'amanat_extracts_ir_attach_rel',
        'extracts_id',
        'attachment_id',
        string='Выписка',
        tracking=True
    )

    raznesti = fields.Boolean(string='Разнести', tracking=True)
    delete_deliveries = fields.Boolean(string='Удалить выписки разнос')

    bank = fields.Selection(
        [
            ('mti', 'МТИ'),
            ('sberbank', 'Сбербанк'),
            ('sovkombank', 'Совкомбанк'),
            ('morskoy', 'Морской'),
            ('ingosstrah', 'Ингосстрах'),
            ('rosbank', 'Росбанк'),
            ('sdm_bank', 'СДМ банк'),
            ('vtb', 'ВТБ'),
            ('nbs', 'НБС'),
            ('zenit', 'Зенит'),
            ('zarechie', 'Заречье'),
            ('absolut', 'Абсолют'),
        ],
        string='Банк',
        tracking=True
    )

    extract_delivery_ids = fields.Many2many(
        'amanat.extract_delivery',
        'amanat_extracts_extract_rel',
        'extracts_id',
        'extract_id',
        string='Выписка разнос',
        tracking=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered('raznesti'):
            try:
                record._process_vypiska_attachments()
            except Exception as e:
                _logger.error("Failed to process attachment for extract %s on create: %s", record.name, e)
            finally:
                record.with_context(no_log=True, skip_automation=True).write({'raznesti': False})
        return records

    def write(self, vals):
        res = super(AmanatExtracts, self).write(vals)

        if vals.get('delete_deliveries'):
            for record in self.filtered(lambda r: r.delete_deliveries):
                record._action_delete_deliveries()
                record.with_context(no_log=True).write({'delete_deliveries': False})

        if vals.get('raznesti'):
            for record in self.filtered(lambda r: r.raznesti):
                try:
                    record._process_vypiska_attachments()
                except Exception as e:
                    _logger.error("Failed to process attachment for extract %s: %s", record.name, e)
                    raise UserError(f"Ошибка обработки выписки {record.name}: {e}")
                finally:
                    record.with_context(no_log=True, skip_automation=True).write({'raznesti': False})
        return res

    def _action_delete_deliveries(self):
        self.ensure_one()
        count = len(self.extract_delivery_ids)
        if count > 0:
            # The records are deleted from the database, and the relation is cleared.
            self.extract_delivery_ids.unlink()
            self.message_post(body=f"Удалено {count} записей 'Выписка разнос'.")
        else:
            self.message_post(body="Связанные записи 'Выписка разнос' для удаления отсутствуют.")
        return True

    def _process_vypiska_attachments(self):
        self.ensure_one()
        if not self.vypiska_ids:
            raise UserError("В поле 'Выписка' нет прикрепленного файла.")

        attachment = self.vypiska_ids[0]

        if not attachment.datas:
            raise UserError("Прикрепленный файл пуст или поврежден.")

        try:
            file_content_bytes = base64.b64decode(attachment.datas)
            file_content = file_content_bytes.decode('windows-1251')
        except Exception as e:
            _logger.error("Cannot decode attachment %s: %s", attachment.name, e)
            raise UserError(f"Не удалось прочитать файл '{attachment.name}'. Файл поврежден или имеет неверную кодировку.")

        try:
            extracted_docs = self._parse_sections(file_content)
            self.message_post(body=f"Найдено документов в файле: {len(extracted_docs)}. Начинаю обработку...")

            if not extracted_docs:
                return

            all_payers = self.env['amanat.payer'].search_read([], ['inn'])
            payers_map = {str(p['inn']).replace(' ', ''): p['id'] for p in all_payers if p.get('inn')}
            
            range_record = self.env['amanat.ranges'].search([], limit=1)
            if not range_record:
                raise UserError("Не найдена запись в 'Диапазонах'. Создайте хотя бы одну запись и попробуйте снова.")

            records_to_create_vals = []
            processed_keys = set()
            skipped_inn_count = 0
            skipped_parsing_count = 0
            skipped_duplicate_count = 0
            duplicate_file_messages = []
            duplicate_db_messages = []
            created_messages = []

            for doc in extracted_docs:
                payer_inn = self._extract_inn_string(doc.get('payerINN'))
                receiver_inn = self._extract_inn_string(doc.get('receiverINN'))

                if not payer_inn or not receiver_inn or payer_inn == receiver_inn:
                    _logger.warning(
                        "Skipping record due to INN issue. Payer INN: %s, Receiver INN: %s, Payer: %s, Receiver: %s",
                        doc.get('payerINN'), doc.get('receiverINN'), doc.get('payer'), doc.get('receiver')
                    )
                    skipped_inn_count += 1
                    continue

                payer_id = self._get_or_create_payer_record_by_inn(payer_inn, doc.get('payer'), payers_map)
                receiver_id = self._get_or_create_payer_record_by_inn(receiver_inn, doc.get('receiver'), payers_map)
                
                if not payer_id or not receiver_id:
                    # This case might be implicitly handled by the INN check, but good to have
                    _logger.warning(
                        "Skipping record due to missing Payer/Receiver ID. Payer INN: %s, Receiver INN: %s",
                        payer_inn, receiver_inn
                    )
                    skipped_inn_count += 1
                    continue

                parsed_date = self._parse_date(doc.get('date'))
                parsed_amount = self._parse_amount(doc.get('amount'))

                if not parsed_date or parsed_amount is None:
                    skipped_parsing_count += 1
                    continue

                new_record_data = {
                    'date': parsed_date,
                    'amount': parsed_amount,
                    'payer': payer_id,
                    'recipient': receiver_id,
                    'payment_purpose': (doc.get('paymentPurpose') or '').replace('\n', ' ').strip(),
                    'document_id': self.id,
                    'range_field': range_record.id,
                }

                try:
                    parsed_number = int(float(doc.get('number', '0')))
                    if parsed_number > 0:
                        new_record_data['serial_number'] = parsed_number
                except (ValueError, TypeError):
                    pass
                
                # --- Start Duplicate Check ---
                # Key based on core data
                key1 = (
                    new_record_data['payer'],
                    new_record_data['recipient'],
                    new_record_data['amount'],
                    new_record_data['date']
                )
                # More specific key if serial number exists
                key2 = None
                if new_record_data.get('serial_number'):
                    key2 = (
                        new_record_data['payer'],
                        new_record_data['recipient'],
                        new_record_data.get('serial_number'),
                        new_record_data['date']
                    )

                is_duplicate = self._is_duplicate_record(new_record_data)
                _logger.info("DEBUG: Результат проверки дубликата: %s", is_duplicate)

                if is_duplicate:
                    _logger.warning(
                        "ДУБЛИКАТ В БД: Пропускаем запись. Плательщик: %s (ИНН: %s), Получатель: %s (ИНН: %s), "
                        "Сумма: %s, Дата: %s, Номер документа: %s, Назначение: %s",
                        doc.get('payer', 'Не указан'),
                        payer_inn,
                        doc.get('receiver', 'Не указан'),
                        receiver_inn,
                        parsed_amount,
                        parsed_date,
                        doc.get('number', 'Не указан'),
                        (doc.get('paymentPurpose') or '').replace('\n', ' ').strip()[:100]
                    )
                    skipped_duplicate_count += 1
                    
                    # Добавляем сообщение о дубликате в БД (не больше 10)
                    if len(duplicate_db_messages) < 10:
                        duplicate_db_messages.append(
                            f"{doc.get('payer', 'Не указан')} → {doc.get('receiver', 'Не указан')}, "
                            f"сумма: {parsed_amount}, дата: {parsed_date}, №: {doc.get('number', 'Не указан')}"
                        )
                    continue
                # --- End Duplicate Check ---

                records_to_create_vals.append(new_record_data)
                processed_keys.add(key1)
                if key2:
                    processed_keys.add(key2)
                
                # Добавляем сообщение о новой записи (не больше 10)
                if len(created_messages) < 10:
                    created_messages.append(
                        f"✅ СОЗДАНО: {doc.get('payer', 'Не указан')} → {doc.get('receiver', 'Не указан')}, "
                        f"сумма: {parsed_amount}, дата: {parsed_date}, №: {doc.get('number', 'Не указан')}"
                    )
            
            created_count = 0
            if records_to_create_vals:
                _logger.info("DEBUG: Создаем %d записей в amanat.extract_delivery", len(records_to_create_vals))
                for i, record_vals in enumerate(records_to_create_vals):
                    _logger.info("DEBUG: Запись %d: %s", i+1, record_vals)
                try:
                    created_records = self.env['amanat.extract_delivery'].create(records_to_create_vals)
                    self.extract_delivery_ids |= created_records
                    created_count = len(created_records)
                    _logger.info("Created %d 'amanat.extract_delivery' records for extract %s", created_count, self.name)
                except Exception as create_error:
                    _logger.error("DEBUG: Ошибка при создании записей: %s", create_error)
                    _logger.error("DEBUG: records_to_create_vals: %s", records_to_create_vals)
                    raise

            summary_message = f"""
                Обработка завершена — 
                Создано новых записей: {created_count} ;
                Пропущено дубликатов: {skipped_duplicate_count} ;
                Пропущено из-за проблем с ИНН: {skipped_inn_count} ;
                Пропущено из-за ошибок парсинга (дата/сумма): {skipped_parsing_count} .
                Автоматическое сопоставление с заявками происходит при создании каждой записи
            """
            self.message_post(body=summary_message)
            
            # Отправляем сообщения о дубликатах (не больше 5)
            if duplicate_file_messages:
                duplicate_msg = duplicate_file_messages[:5]  # Ограничиваем 5 сообщениями
                if len(duplicate_file_messages) > 5:
                    duplicate_msg.append(f"... и еще {len(duplicate_file_messages) - 5} дубликатов")
                self.message_post(body=f"Найденные дубликаты в файле: {'; '.join(duplicate_msg)}")

            if duplicate_db_messages:
                duplicate_msg = duplicate_db_messages[:5]  # Ограничиваем 5 сообщениями
                if len(duplicate_db_messages) > 5:
                    duplicate_msg.append(f"... и еще {len(duplicate_db_messages) - 5} дубликатов")
                self.message_post(body=f"Найденные дубликаты в БД: {'; '.join(duplicate_msg)}")

            # Отправляем сообщения о созданных записях (не больше 5)
            if created_messages:
                created_msg = created_messages[:5]  # Ограничиваем 5 сообщениями
                if created_count > 5:
                    created_msg.append(f"... и еще {created_count - 5} записей")
                self.message_post(body=f"Созданные записи: {'; '.join(created_msg)}")

            # Автоматический запуск обработки СТЕЛЛАР/ТДК/ИНДОТРЕЙД РФ
            self.env['amanat.extract_delivery']._run_stellar_tdk_logic()
            
            # Примечание: автоматическое сопоставление с заявками теперь происходит
            # при создании каждой записи extract_delivery в методе create()

        except Exception as e:
            _logger.error("Error during record creation for extract %s: %s", self.name, e, exc_info=True)
            raise UserError(f"Ошибка на этапе создания записей: {e}")

    def _parse_sections(self, content):
        documents = []
        sections = content.split("СекцияДокумент")
        for section in sections:
            if not section.strip():
                continue
            
            fields = {}
            date_match = re.search(r"Дата=(.+)", section)
            fields['date'] = date_match.group(1) if date_match else None
            amount_match = re.search(r"Сумма=(.+)", section)
            fields['amount'] = amount_match.group(1) if amount_match else None
            number_match = re.search(r"Номер=(.+)", section)
            fields['number'] = number_match.group(1) if number_match else None
            
            payer_match = re.search(r"Плательщик=(.+)", section) or re.search(r"Плательщик1=(.+)", section)
            raw_payer = payer_match.group(1) if payer_match else None
            fields['payer'] = self._clean_contractor_name(raw_payer)

            receiver_match = re.search(r"Получатель=(.+)", section) or re.search(r"Получатель1=(.+)", section)
            raw_receiver = receiver_match.group(1) if receiver_match else None
            fields['receiver'] = self._clean_contractor_name(raw_receiver)

            payer_inn_match = re.search(r"ПлательщикИНН=(.+)", section)
            fields['payerINN'] = payer_inn_match.group(1) if payer_inn_match else None
            receiver_inn_match = re.search(r"ПолучательИНН=(.+)", section)
            fields['receiverINN'] = receiver_inn_match.group(1) if receiver_inn_match else None
            payment_purpose_match = re.search(r"НазначениеПлатежа=(.+)", section)
            fields['paymentPurpose'] = payment_purpose_match.group(1) if payment_purpose_match else None

            if fields.get('date') or fields.get('amount'):
                documents.append({k: v.strip() if v else v for k, v in fields.items()})
        return documents

    def _extract_inn_string(self, inn):
        if not inn:
            return None
        cleaned = re.sub(r'\D', '', str(inn))
        return cleaned if cleaned else None

    def _clean_contractor_name(self, name):
        if not name:
            return ''
        return re.sub(r'^ИНН\s*\d+\s*', '', str(name), flags=re.IGNORECASE).strip()

    def _parse_date(self, date_str):
        if not date_str:
            return None
        try:
            # Format DD.MM.YYYY
            return datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
        except ValueError:
            return None

    def _parse_amount(self, amount_str):
        if not amount_str:
            return None
        amount_str = amount_str.replace(' ', '').replace(',', '.')
        try:
            return float(amount_str)
        except (ValueError, TypeError):
            return None

    def _get_or_create_payer_record_by_inn(self, inn_string, payer_name, payers_map):
        if not inn_string:
            return None
        
        if inn_string in payers_map:
            return payers_map[inn_string]

        cleaned_name = self._clean_contractor_name(payer_name) or "(без имени)"
        
        try:
            # More robust way to find/create contragent to avoid race conditions and duplicates
            existing_contragent = self.env['amanat.contragent'].search([('name', '=', cleaned_name)], limit=1)
            if not existing_contragent:
                existing_contragent = self.env['amanat.contragent'].create({'name': cleaned_name})

            new_payer = self.env['amanat.payer'].create({
                'name': cleaned_name,
                'inn': inn_string,
                'contragents_ids': [(4, existing_contragent.id)]
            })
            payers_map[inn_string] = new_payer.id
            _logger.info("Created new Payer '%s' (INN: %s) and linked to Contragent.", cleaned_name, inn_string)
            return new_payer.id
        except Exception as e:
            _logger.error("Failed to create Payer/Contragent for INN %s: %s", inn_string, e)
            return None

    def _is_duplicate_record(self, new_record_vals):
        ExtractDelivery = self.env['amanat.extract_delivery']
        # Domain fields must exist and not be None
        required_fields = ['payer', 'recipient', 'amount', 'date']
        if any(new_record_vals.get(f) is None for f in required_fields):
            _logger.info("DEBUG: Недостаточно данных для проверки дубликатов. Доступные поля: %s", new_record_vals)
            return False # Not enough data to check for duplicates

        # Отладка: проверим, что мы ищем
        _logger.info("DEBUG: Проверяем дубликат для записи:")
        _logger.info("  - payer: %s (ID: %s)", self.env['amanat.payer'].browse(new_record_vals['payer']).name if new_record_vals.get('payer') else 'None', new_record_vals.get('payer'))
        _logger.info("  - recipient: %s (ID: %s)", self.env['amanat.payer'].browse(new_record_vals['recipient']).name if new_record_vals.get('recipient') else 'None', new_record_vals.get('recipient'))
        _logger.info("  - amount: %s", new_record_vals.get('amount'))
        _logger.info("  - date: %s", new_record_vals.get('date'))
        _logger.info("  - serial_number: %s", new_record_vals.get('serial_number'))

        domain1 = [
            ('payer', '=', new_record_vals['payer']),
            ('recipient', '=', new_record_vals['recipient']),
            ('amount', '=', new_record_vals['amount']),
            ('date', '=', new_record_vals['date']),
            ('serial_number', '=', new_record_vals['serial_number']),
        ]
        _logger.info("DEBUG: Domain1 для поиска: %s", domain1)
        count1 = ExtractDelivery.search_count(domain1)
        _logger.info("DEBUG: Найдено записей по domain1: %d", count1)

        if count1 > 0:
            existing_records = ExtractDelivery.search(domain1, limit=5)
            for rec in existing_records:
                _logger.info("  Найденная запись ID %s: payer=%s, recipient=%s, amount=%s, date=%s, serial_number=%s", rec.id, rec.payer.name, rec.recipient.name, rec.amount, rec.date, rec.serial_number)
            return True

        # if new_record_vals.get('serial_number'):
        #     domain2 = [
        #         ('payer', '=', new_record_vals['payer']),
        #         ('recipient', '=', new_record_vals['recipient']),
        #         ('serial_number', '=', new_record_vals['serial_number']),
        #         ('date', '=', new_record_vals['date']),
        #     ]
        #     _logger.info("DEBUG: Domain2 для поиска (без дублирования serial_number): %s", domain2)
        #     count2 = ExtractDelivery.search_count(domain2)
        #     _logger.info("DEBUG: Найдено записей по domain2: %d", count2)

        #     if count2 > 0:
        #         existing_records = ExtractDelivery.search(domain2, limit=5)
        #         for rec in existing_records:
        #             _logger.info("  Найденная запись ID %s: payer=%s, recipient=%s, amount=%s, date=%s, serial_number=%s",
        #                        rec.id, rec.payer.name, rec.recipient.name, rec.amount, rec.date, rec.serial_number)
        #         return True

        _logger.info("DEBUG: Дубликат НЕ найден, запись будет создана")
        return False
