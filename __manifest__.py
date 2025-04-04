{
    'name': 'Amanat: Переводы',
    'version': '2.0',
    'summary': 'Amanat',
    'description': 'Модуль проекта Amanat',
    'author': 'IncubeAI (Мирас)',
    'category': 'Amanat',
    'depends': ['base', 'mail', 'base_automation', 'web', 'base_setup'],
    'data': [
        # sidebar
        'templates/webclient.xml',
        'views/res_users.xml',
        'views/res_config_settings.xml',

        # 1) Сначала объявляем группы
        'security/security_groups.xml',

        # 2) Затем прописываем права на модели
        'security/ir.model.access.csv',

        # 3) Затем правила доступа (record rules). Можно до или после menu.xml, 
        #    главное, чтобы security_groups.xml был до него.
        'security/record_rules.xml',

        # 4) Потом представления для моделей
        'views/automation_views.xml',
        'views/contragent_views.xml',
        'views/activity_views.xml',
        'views/payer_views.xml',
        'views/transfer_views.xml',
        'views/wallet_views.xml',
        'views/order_views.xml',
        'views/money_views.xml',
        'views/reconciliation_views.xml',
        'views/ranges_views.xml',
        'views/rates_views.xml',
        'views/writeoff_views.xml',
        'views/conversion_views.xml',
        'views/extract_delivery_views.xml',
        'views/country_views.xml',
        'views/zayavka_views.xml',
        'views/reserve_views.xml',
        'views/kassa_ivan_views.xml',
        'views/kassa_2_views.xml',
        'views/kassa_3_views.xml',
        'views/price_list_partners_views.xml',
        'views/price_list_payer_profit_views.xml',
        'views/tasks_views.xml',
        'views/payment_views.xml',
        'views/gold_deal_views.xml',
        'views/partner_gold_views.xml',
        'views/extracts_views.xml',
        'views/sverka_files_views.xml',
        'views/period_views.xml',
        'views/investment_views.xml',
        'views/manager_views.xml',

        # 5) Затем создаём/обновляем меню (поскольку оно ссылается на группы)
        'views/menu.xml',

        # 'static/src/xml/templates.xml',

        # 6) Остальные файлы
        'data/transfer_sequence.xml',
        'data/ranges_sequence.xml',
        'data/rates_sequence.xml',
        'data/conversion_sequence.xml',
        'data/zayavka_sequence.xml',
        'data/kassa_ivan_sequence.xml',
        'data/kassa_2_sequence.xml',
        'data/kassa_3_sequence.xml',
        'data/gold_deal_sequence.xml',
        'data/partner_gold_sequence.xml',
        'data/order_sequence.xml',
        'data/conversion_sequence.xml',
    ],

    'assets': {
        'web._assets_primary_variables': [
            'amanat/static/src/scss/variables.scss',
        ],
        'web._assets_backend_helpers': [
            'amanat/static/src/scss/mixins.scss',
        ],
        'web.assets_web_dark': [
            (
                'after',
                'amanat/static/src/scss/variables.scss',
                'amanat/static/src/scss/variables.dark.scss',
            ),
        ],
        'web.assets_backend': [
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'amanat/static/src/webclient/webclient.js',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.xml',
                'amanat/static/src/webclient/webclient.xml',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'amanat/static/src/webclient/menus/app_menu_service.js',
            ),
            (
                'after',
                'web/static/src/webclient/webclient.js',
                'amanat/static/src/webclient/appsbar/appsbar.js',
            ),
            'amanat/static/src/webclient/webclient.scss',
            'amanat/static/src/webclient/appsbar/appsbar.xml',
            'amanat/static/src/webclient/appsbar/appsbar.scss',
        ],
    },

    'installable': True,
    'application': True,
}
