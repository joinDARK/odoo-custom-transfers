# Анализ с помощью YandexGPT
Все методы для анализа документов (кроме SWIFT-ов, потому что это делал Мирас) находятся в файле `ygpt_analyse.py`. Также есть файл `ygpt_config.py` (директория `models`) и в нем определена модель `class ResConfigSettingsYandexGPT(models.TransientModel)`, которая наследуется от `res.config.settings`. В ней находятся поля для хранения промптов, API-ключа и Folder ID (в облаке Yandex Cloud). Все эти поля можно увидеть в Настройках внизу. Редактируем промпты в настройках.

Далее про `ygpt_analyse.py`...

## ypgt_analyse.py
Здесь хранятся методы для анализа документов. Анализ происходит по следующем алгоритму: Загружаются документ или скриншот (картинка) -> Нейронке отправляется текст, полученный из файлов -> Нейронка возвращает текст ввиде json-а -> Вытаскиваем json из текста и конвертируем в реальный json -> Анализируем json и заполняем поля (если они пустые)

В файле `documents.py` есть методы, с помощью которые получаем текст из DOCX/DOC/XLSX/PDF. После этого вызываем метод, который отправляет запрос по Yandex API, который возвращает текст с json ответом. Мы находит этот json, перебирая строку с помощью Python и конвертируем полученный json в словарь. Далее проходимся по этому словарю и подготавливаем словарь для обновления полей, а после обновляем значения. Если же значение было заполнено или не нашлись связанное значение, то вылезет уведомление об этом на сайте. Анализ изображение проходит такой же путь, только в начале мы отправляем запрос в Yandex OCR API, где возвращается текст на изображении, а потом этот текст идет в нейронку.

Вот методы, которые определены в `ygpt_analyse.py`:
- `def analyze_document_with_yandex_gpt(self, content, prompt_type="zayavka")` — выполняет запрос в yandex gpt и затем вызывает метод обновления полей в записи
- `def analyze_screen_sber_images_with_yandex_gpt(self)` — выполняет запрос в Yandex OCR для изображения и полученный текст отправляем в метод `def analyze_document_with_yandex_gpt(self, content, prompt_type="zayavka")`
- `def zayavka_analyse_with_yandex_gpt(self)` — метод для анализа поля `zayavka_attachments` (Заявка Вход)
- `def analyze_assignment_with_yandex_gpt(self)` — метод для анализа поручения (`assignment_attachments`)
- `def analyze_pdf_attachments_with_yandex_gpt(self, attachment, prompt_type="zayavka")` — метод для анализа PDF-файла из `zayavka_attachments` с помощью Yandex Vision OCR API и отправляет распознанный текст в YandexGPT
- `def _notify_user_simple(self, title, message, warning=False, sticky=False)` — метод для отправки уведомления пользователю
- `def _update_fields_from_gpt_response(self, gpt_response)` — метод для обновления полей в заявке
- `def _get_field_label(self, field_name)` — возвращает значение из атрибута `string` в поле
- `def _handle_special_fields(self, parsed_data, update_values)` — метод для специальной обработки сложный полей (например many2many, many2one, date и тп)
- `def _get_screen_sber_images_base64(self)` — возвращает изображение, закодированное в base64. Используется для анализа сбер скрина через Yandex OCR API
- `def _get_pdf_attachments_base64(self, attachment)` — возвращает список dict с полями name, mimetype, base64 для PDF файлов
- `def _send_image_to_yandex_gpt_vision(self, image_info)` — метод для отправки изображения в Yandex OCR API. Возвращает распознанный текст
- `def _normalize_payer_name(self, name)` — метод для нормализация текста, для поиска плательщика по имени
- `def _advanced_payer_search(self, search_text)` — продвинутый метод поиска подходящей записи в модели `amanat.payer`
- `def _calculate_similarity(self, str1, str2)` — метод для подсчета "схожести"
- `def _advanced_country_search(self, search_text)` — продвинутый метод поиска подходящей записи в модели `amanat.country`
- `def _advanced_contragent_search(self, search_text, context_type="контрагент")` — продвинутый метод поиска подходящей записи в модели `amanat.contragent`
- `def _get_yandex_gpt_config(env, prompt_type=None)` — возвращает конфиг YandexGPT из системных параметров
- `def _make_headers(api_key, folder_id)` — возвращает загаловок для запроса через API

Также про некоторые константные переменные:
- `URL` — url для запроса по YandexGPT API
- `OCR_URL` — url для запроса по Yandex OCR API
- `PROMPT` — дефолтные промпт (я вообще хз, используется ли он в итоге или нет)
- `UPDATE_FIELDS` — массив полей `amanat.zayavka` для обновления
- `FIELD_MAPPING` — словарь для обновления полей. Он должен был выступать для маппинга полей из json-а от YGPT, но сейчас нужен для обновления специальных полей (для дата или many2many/many2one/one2many и тп)

*P.S. За остальные методы я не шарю =)*