# custom_transfers/__manifest__.py
{
    'name': 'Custom Transfers',
    'version': '1.0',
    'summary': 'Управление переводами',
    'description': 'Модуль для управления переводами с контрагентами и плательщиками',
    'author': 'Miras',
    'category': 'Custom',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/contragent_views.xml',
        'views/payer_views.xml',
        'views/transfer_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
}
