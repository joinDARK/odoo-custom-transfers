from odoo import models, fields


class ResConfigSettingsYandexGPT(models.TransientModel):
    _inherit = 'res.config.settings'

    ygpt_api_key = fields.Char(
        string='YandexGPT API ключ',
        config_parameter='amanat.ygpt.api_key',
    )
    ygpt_folder_id = fields.Char(
        string='YandexGPT Folder ID',
        config_parameter='amanat.ygpt.folder_id',
    )
    ygpt_prompt_for_zayavka_analyse = fields.Char(
        string='YandexGPT промпт для анализа заявки',
        config_parameter='amanat.ygpt.prompt_for_zayavka_analyse',
        size=2000,
        help='Базовый системный промпт для анализа заявки вход, который будет отправляться вместе с сообщением пользователя.'
    )
    ygpt_prompt_for_sber_screen_analyse = fields.Char(
        string='YandexGPT промпт для анализа сбербанка',
        config_parameter='amanat.ygpt.prompt_for_sber_screen_analyse',
        size=2000,
        help='Базовый системный промпт для анализа сбербанка, который будет отправляться вместе с сообщением пользователя.'
    )
    ygpt_prompt_for_assignment_analyse = fields.Char(
        string='YandexGPT промпт для анализа поручения',
        config_parameter='amanat.ygpt.prompt_for_assignment_analyse',
        size=2000,
        help='Базовый системный промпт для анализа поручения, который будет отправляться вместе с сообщением пользователя.'
    )