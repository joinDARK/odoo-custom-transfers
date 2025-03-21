{
    'name': 'Amanat: Переводы',
    'version': '2.0',
    'summary': 'Amanat',
    'module': 'amanat',
    'description': 'Модуль проекта Amanat',
    'author': 'IncubeAI (Мирас)',
    'category': 'Amanat',
    'depends': ['base', 'mail'],
    'data': [
        # 1) Сначала объявляем группы
        'security/security_groups.xml',

        # 2) Затем прописываем права на модели
        'security/ir.model.access.csv',

        # 3) Затем создаём/обновляем меню (поскольку оно ссылается на группы)
        'views/menu.xml',

        # 4) Затем правила доступа (record rules). Можно до или после menu.xml, 
        #    главное, чтобы security_groups.xml был до него.
        'security/record_rules.xml',

        # 5) Остальные представления
        'views/contragent_views.xml',
        'views/activity_views.xml',
        'views/payer_views.xml',
        'views/transfer_views.xml',

        # 6) Данные
    ],
    'installable': True,
    'application': True,
}
