{
    'name': 'Amanat: Переводы',
    'version': '2.0',
    'summary': 'Amanat',
    'description': 'Модуль проекта Amanat',
    'author': 'IncubeAI (Мирас)',
    'category': 'Amanat',
    'depends': ['base', 'mail', 'base_automation', 'web'],
    'data': [
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

        # 5) Затем создаём/обновляем меню (поскольку оно ссылается на группы)
        'views/menu.xml',


        # 'static/src/xml/templates.xml',

        # 6) Остальные файлы
        'data/transfer_sequence.xml',
        'data/ranges_sequence.xml',
        'data/rates_sequence.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'amanat/static/src/js/amanat.js',
    #         'amanat/static/src/css/amanat.css',
    #     ],
    # },

    'installable': True,
    'application': True,
}
