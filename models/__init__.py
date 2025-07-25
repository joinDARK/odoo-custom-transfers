# crm_amanat/models/__init__.py
from . import list_view_mixin
from . import base_model
from . import dashboard
from . import analytics_dashboard
from . import zayavka_fiks_dashboard
from . import test_realtime
from . import activity
from . import contragent
from . import payer
from . import transfer
from . import wallet
from . import reconciliation
from . import order
from . import money
from . import ranges
from . import rate
from . import writeoff
from . import сonversion
from . import extract_delivery
from . import country
from . import zayavka
from . import reserve
from . import kassa_ivan
from . import kassa_2
from . import kassa_3
from . import price_list_partners
from . import price_list_payer_profit
from . import tasks
from . import payment
from . import gold_deal
from . import partner_gold
from . import investment
from . import manager
from . import extracts
from . import sverka_files
from . import kassa_files
from . import period
from . import price_list_payer_carrying_out
from . import payment_order_rule
from . import money_cost_rule
from . import expense_rule
from . import zayavka_date_range_wizard
from . import zayavka_kassa_wizard
from . import reconciliation_date_range_wizard
from . import contragent_gold


# SWIFT integration
from . import swift
from . import swift_api_config
from . import mail_bot_extension
from . import zayavka_swift_extension
from . import discuss_channel_extension

# sidebar
from . import ir_http
from . import res_users
from . import res_company
from . import res_config_settings
from . import ir_attachment

from . import signature_library
from . import zayavka_signature_position
from . import zayavka_signature_assignment

# Calculators
from . import calculators