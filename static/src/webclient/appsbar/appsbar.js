/** @odoo-module **/

import { useState } from '@odoo/owl';
import { Component, onWillUnmount } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { url } from '@web/core/utils/urls';

export class AppsBar extends Component {
    static template = 'amanat.AppsBar';

    setup() {
        this.actionService = useService("action");
        this.companyService = useService('company');
        this.appMenuService = useService('app_menu');
        this.orm = useService('orm');

        this.menuData = [
            {
                name: "Валютные операции",
                items: [
                    { name: "Перевод", action: "amanat.transfer_action" },
                    { name: "Конвертации", action: "amanat.conversion_action" },
                    { name: "Валютный резерв", action: "amanat.reserve_action" },
                    { name: "Инвестиции", action: "amanat.investment_action" },
                ],
            },
            {
                name: "Вычислительные таблицы",
                items: [
                    { name: "Ордер", action: "amanat.order_action" },
                    { name: "Контейнер", action: "amanat.money_action" },
                    { name: "Сверка", action: "amanat.reconciliation_action" },
                    { name: "Сверка файлы", action: "amanat.action_amanat_sverka_files" },
                    { name: "Касса файлы", action: "amanat.action_amanat_kassa_files" },
                ],
            },
            {
                name: "Справочники",
                items: [
                    { name: "Контрагенты", action: "amanat.contragent_action" },
                    { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                    { name: "Плательщики", action: "amanat.payer_action" },
                    { name: "Страны", action: "amanat.country_action" },
                    { name: "Менеджеры", action: "amanat.manager_action" },
                    { name: "Библиотека подписей", action: "amanat.signature_library_action" },
                    { name: "Шаблоны документов", action: "amanat.template_library_action" },
                    { name: "Курс Джесс", action: "amanat.jess_rate_action" },
                ],
            },
            {
                name: "Золото",
                items: [
                    { name: "Золото сделка", action: "amanat.gold_deal_action" },
                    { name: "Партнеры золото", action: "amanat.partner_gold_action" },
                    { name: "Контрагенты золото", action: "amanat.contragent_gold_action" },
                ],
            },
            {
                name: "Выписки",
                items: [
                    { name: "Выписки", action: "amanat.action_amanat_extracts" },
                    { name: "Выписка разнос", action: "amanat.extract_delivery_action" },
                ],
            },
            {
                name: "Прайс листы",
                items: [
                    { name: "Прайс лист роялти", action: "amanat.price_list_royalty_action" },
                    { name: "Прайс лист партнеры", action: "amanat.price_list_partners_action" },
                    { name: "Прайс лист Плательщика", action: "amanat.price_list_payer_profit_action" },
                    { name: "Прайс лист Плательщика За проведение", action: "amanat.price_list_payer_carrying_out_action" },
                ],
            },
            {
                name: "Правила",
                items: [
                    { name: "Правила Расход на операционную деятельность", action: "amanat.action_expense_rule" },
                    { name: "Правила Себестоимость денег", action: "amanat.action_money_cost_rule" },
                    { name: "Правила Платежка РФ", action: "amanat.action_payment_order_rule" },
                ],
            },
            {
                name: "Кассы",
                items: [
                    { name: "Касса Иван", action: "amanat.kassa_ivan_action" },
                    { name: "Касса 2", action: "amanat.kassa_2_action" },
                    { name: "Касса 3", action: "amanat.kassa_3_action" },
                ],
            },
            {
                name: "Анализ",
                items: [
                    { name: "Аналитический дашборд", action: "amanat.action_amanat_analytics_dashboard_js" },
                    { name: "Дашборд", action: "amanat.action_amanat_dashboard_js" },
                    { name: "Фикс заявка", action: "amanat.zayavka_fiks_dashboard_action_menu" },
                ],
            },
            {
                name: "Калькуляторы",
                items: [
                    { name: "Спред", action: "amanat.action_amanat_calculator_spread" },
                    { name: "Расчет добавка в $ Совком", action: "amanat.action_amanat_calculator_50_usd" },
                    { name: "Расчет добавка в $ для всех", action: "amanat.action_amanat_calculator_wizard" },
                    { name: "Калькулятор для фиксированного вознаграждения", action: "amanat.action_amanat_calculator_fixed_fee" },
                ],
            },
            {
                name: "Заявки",
                action: "amanat.zayavka_action",
                actionMethod: "openZayvaki",
            },
            {
                name: "Автоматизации",
                action: "amanat.action_automation_for_amanat",
                actionMethod: "openAutomations",
            },
            {
                name: "Логи",
                action: "amanat.activity_action",
                actionMethod: "openLogs",
            },
            {
                name: "Остальное",
                items: [
                    { name: "Диапазоны", action: "amanat.ranges_action" },
                    { name: "Курсы к доллару", action: "amanat.rates_action" },
                    { name: "Платежи", action: "amanat.payment_action" },
                    { name: "Период", action: "amanat.action_amanat_period" },
                    { name: "Списания", action: "amanat.writeoff_action" },
                    { name: "Кошелек", action: "amanat.wallet_action" },
                ],
            },
        ];

        this.state = useState({
            isCollapsed: false,
            activeMenuIndex: null,
            isAmanat: false,
            appName: '',
            activeItem: null,
            activeMainMenuIndex: null,
            sidebarWidth: this.getSavedSidebarWidth(),
            userGroups: {},
        });
        
        // Переменные для изменения размера
        this.isResizing = false;
        this.startX = 0;
        this.startWidth = 0;
        
        // Привязываем методы для обработчиков событий
        this.boundOnMouseMove = this.onMouseMove.bind(this);
        this.boundStopResize = this.stopResize.bind(this);

        // Загружаем группы пользователя
        this.loadUserGroups();

        const refreshMenuState = () => {
            const currentApp = this.appMenuService.getCurrentApp();
            if (currentApp) {
                this.state.appName = currentApp.name;
                this.state.isAmanat = (currentApp.name === 'ТДК');
                this.state.activeMenuIndex = null;
                
                // Управляем сайдбаром в зависимости от модуля
                if (this.state.isAmanat) {
                    // В модуле Amanat - показываем сайдбар
                    document.body.classList.remove('mk_sidebar_disabled');
                    if (this.state.isCollapsed) {
                        document.documentElement.style.setProperty('--sidebar-width', '0px');
                        document.body.classList.add('mk_sidebar_hidden');
                    } else {
                        document.documentElement.style.setProperty('--sidebar-width', this.state.sidebarWidth + 'px');
                        document.body.classList.remove('mk_sidebar_hidden');
                    }
                } else {
                    // Не в модуле Amanat - полностью отключаем сайдбар
                    document.documentElement.style.setProperty('--sidebar-width', '0px');
                    document.body.classList.add('mk_sidebar_disabled');
                    document.body.classList.remove('mk_sidebar_hidden');
                }
            }
        };
        refreshMenuState();
        
        // Устанавливаем начальное состояние сайдбара
        if (this.state.isAmanat) {
            document.body.classList.remove('mk_sidebar_disabled');
            if (this.state.isCollapsed) {
                document.documentElement.style.setProperty('--sidebar-width', '0px');
                document.body.classList.add('mk_sidebar_hidden');
            } else {
                document.documentElement.style.setProperty('--sidebar-width', this.state.sidebarWidth + 'px');
                document.body.classList.remove('mk_sidebar_hidden');
            }
        } else {
            // По умолчанию отключаем сайдбар если не в Amanat
            document.documentElement.style.setProperty('--sidebar-width', '0px');
            document.body.classList.add('mk_sidebar_disabled');
            document.body.classList.remove('mk_sidebar_hidden');
        }

        this.env.bus.addEventListener('MENUS:APP-CHANGED', refreshMenuState);
        onWillUnmount(() => {
            this.env.bus.removeEventListener('MENUS:APP-CHANGED', refreshMenuState);
            
            // Очищаем слушатели событий для изменения размера, если они активны
            if (this.isResizing) {
                document.removeEventListener('mousemove', this.boundOnMouseMove);
                document.removeEventListener('mouseup', this.boundStopResize);
                document.body.classList.remove('mk_sidebar_resizing');
            }
            
            // Очищаем все CSS классы и переменные сайдбара при размонтировании
            document.body.classList.remove('mk_sidebar_hidden', 'mk_sidebar_disabled');
            document.documentElement.style.removeProperty('--sidebar-width');
        });

        if (this.companyService.currentCompany.has_appsbar_image) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'appbar_image',
                id: this.companyService.currentCompany.id,
            });
        }
    }

    async loadUserGroups() {
        try {
            this.state.userGroups = await this.orm.call('res.users', 'check_user_groups', []);
        } catch (error) {
            console.error('Error loading user groups:', error);
            this.state.userGroups = {};
        }
    }

    getFilteredMenuData() {
        // Проверка для пользователей с ролью "Казначей" (Ільзіра)
        if (this.state.userGroups.is_treasurer) {
            return [
                {
                    name: "Справочники",
                    items: [
                        { name: "Контрагенты", action: "amanat.contragent_action" },
                        { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                        { name: "Плательщики", action: "amanat.payer_action" },
                        { name: "Страны", action: "amanat.country_action" },
                        { name: "Менеджеры", action: "amanat.manager_action" },
                    ],
                },
                {
                    name: "Выписки",
                    items: [
                        { name: "Выписки", action: "amanat.action_amanat_extracts" },
                        { name: "Выписка разнос", action: "amanat.extract_delivery_action" },
                    ],
                },
                {
                    name: "Заявки",
                    action: "amanat.zayavka_action",
                    actionMethod: "openZayvaki",
                },
            ];
        }

        // Проверка для пользователей с ролью "Транзитные переводы"
        if (this.state.userGroups.is_transit_only) {
            // Если пользователь также является менеджером, показываем расширенное меню
            if (this.state.userGroups.is_manager || this.state.userGroups.is_senior_manager) {
                return [
                    {
                        name: "Валютные операции",
                        items: [
                            { name: "Перевод", action: "amanat.transfer_action" },
                        ],
                    },
                    {
                        name: "Справочники",
                        items: [
                            { name: "Контрагенты", action: "amanat.contragent_action" },
                            { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                            { name: "Страны", action: "amanat.country_action" },
                            { name: "Плательщики", action: "amanat.payer_action" },
                            { name: "Менеджеры", action: "amanat.manager_action" },
                        ],
                    },
                    {
                        name: "Заявки",
                        action: "amanat.zayavka_action",
                        actionMethod: "openZayvaki",
                    },
                    {
                        name: "Калькуляторы",
                        items: [
                            { name: "Спред", action: "amanat.action_amanat_calculator_spread" },
                            { name: "Расчет добавка в $ Совком", action: "amanat.action_amanat_calculator_50_usd" },
                            { name: "Расчет добавка в $ для всех", action: "amanat.action_amanat_calculator_wizard" },
                            { name: "Калькулятор для фиксированного вознаграждения", action: "amanat.action_amanat_calculator_fixed_fee" },
                        ],
                    },
                ];
            } else {
                // Только роль "Транзитные переводы" - показываем минимальное меню
                return [
                    {
                        name: "Валютные операции",
                        items: [
                            { name: "Перевод", action: "amanat.transfer_action" },
                        ],
                    },
                    {
                        name: "Справочники",
                        items: [
                            { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                        ],
                    },
                ];
            }
        }

        if (this.state.userGroups.is_director) {
            return [
                {
                    name: "Валютные операции",
                    items: [
                        { name: "Перевод", action: "amanat.transfer_action" },
                        { name: "Конвертации", action: "amanat.conversion_action" },
                        { name: "Валютный резерв", action: "amanat.reserve_action" },
                        { name: "Инвестиции", action: "amanat.investment_action" },
                    ],
                },
                {
                    name: "Вычислительные таблицы",
                    items: [
                        { name: "Ордер", action: "amanat.order_action" },
                        { name: "Контейнер", action: "amanat.money_action" },
                        { name: "Сверка", action: "amanat.reconciliation_action" },
                        { name: "Сверка файлы", action: "amanat.action_amanat_sverka_files" },
                        { name: "Касса файлы", action: "amanat.action_amanat_kassa_files" },
                    ],
                },
                {
                    name: "Справочники",
                    items: [
                        { name: "Контрагенты", action: "amanat.contragent_action" },
                        { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                        { name: "Плательщики", action: "amanat.payer_action" },
                        { name: "Страны", action: "amanat.country_action" },
                        { name: "Менеджеры", action: "amanat.manager_action" },
                        { name: "Библиотека подписей", action: "amanat.signature_library_action" },
                        { name: "Шаблоны документов", action: "amanat.template_library_action" },
                        { name: "Курс Джесс", action: "amanat.jess_rate_action" },
                    ],
                },
                {
                    name: "Золото",
                    items: [
                        { name: "Золото сделка", action: "amanat.gold_deal_action" },
                        { name: "Партнеры золото", action: "amanat.partner_gold_action" },
                        { name: "Контрагенты золото", action: "amanat.contragent_gold_action" },
                    ],
                },
                {
                    name: "Выписки",
                    items: [
                        { name: "Выписки", action: "amanat.action_amanat_extracts" },
                        { name: "Выписка разнос", action: "amanat.extract_delivery_action" },
                    ],
                },
                {
                    name: "Прайс листы",
                    items: [
                        { name: "Прайс лист партнеры", action: "amanat.price_list_partners_action" },
                        { name: "Прайс лист Плательщика", action: "amanat.price_list_payer_profit_action" },
                        { name: "Прайс лист Плательщика За проведение", action: "amanat.price_list_payer_carrying_out_action" },
                    ],
                },
                {
                    name: "Правила",
                    items: [
                        { name: "Правила Расход на операционную деятельность", action: "amanat.action_expense_rule" },
                        { name: "Правила Себестоимость денег", action: "amanat.action_money_cost_rule" },
                        { name: "Правила Платежка РФ", action: "amanat.action_payment_order_rule" },
                    ],
                },
                {
                    name: "Кассы",
                    items: [
                        { name: "Касса Иван", action: "amanat.kassa_ivan_action" },
                        { name: "Касса 2", action: "amanat.kassa_2_action" },
                        { name: "Касса 3", action: "amanat.kassa_3_action" },
                    ],
                },
                {
                    name: "Анализ",
                    items: [
                        { name: "Аналитический дашборд", action: "amanat.action_amanat_analytics_dashboard_js" },
                        { name: "Дашборд", action: "amanat.action_amanat_dashboard_js" },
                        { name: "Фикс заявка", action: "amanat.zayavka_fiks_dashboard_action_menu" },
                    ],
                },
                {
                    name: "Калькуляторы",
                    items: [
                        { name: "Спред", action: "amanat.action_amanat_calculator_spread" },
                        { name: "Расчет добавка в $ Совком", action: "amanat.action_amanat_calculator_50_usd" },
                        { name: "Расчет добавка в $ для всех", action: "amanat.action_amanat_calculator_wizard" },
                        { name: "Калькулятор для фиксированного вознаграждения", action: "amanat.action_amanat_calculator_fixed_fee" },
                    ],
                },
                {
                    name: "Заявки",
                    action: "amanat.zayavka_action",
                    actionMethod: "openZayvaki",
                }
            ];
        }

        if (this.state.userGroups.is_dilara) {
            return [
                {
                    name: "Справочники",
                    items: [
                        { name: "Контрагенты", action: "amanat.contragent_action" },
                        { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                        { name: "Страны", action: "amanat.country_action" },
                        { name: "Плательщики", action: "amanat.payer_action" },
                        { name: "Менеджеры", action: "amanat.manager_action" },
                        { name: "Курс Джесс", action: "amanat.jess_rate_action" },
                    ],
                },
                {
                    name: "Анализ",
                    items: [
                        { name: "Аналитический дашборд", action: "amanat.action_amanat_analytics_dashboard_js" },
                        { name: "Дашборд", action: "amanat.action_amanat_dashboard_js" },
                        { name: "Фикс заявка", action: "amanat.zayavka_fiks_dashboard_action_menu" },
                    ],
                },
                {
                    name: "Заявки",
                    action: "amanat.zayavka_action",
                    actionMethod: "openZayvaki",
                },
                {
                    name: "Калькуляторы",
                    items: [
                        { name: "Спред", action: "amanat.action_amanat_calculator_spread" },
                        { name: "Расчет добавка в $ Совком", action: "amanat.action_amanat_calculator_50_usd" },
                        { name: "Расчет добавка в $ для всех", action: "amanat.action_amanat_calculator_wizard" },
                        { name: "Калькулятор для фиксированного вознаграждения", action: "amanat.action_amanat_calculator_fixed_fee" },
                    ],
                },
            ];
        }

        if (this.state.userGroups.is_fin_manager_jess) {
            return [
                {
                    name: "Справочники",
                    items: [
                        { name: "Контрагенты", action: "amanat.contragent_action" },
                        { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                        { name: "Страны", action: "amanat.country_action" },
                        { name: "Плательщики", action: "amanat.payer_action" },
                        { name: "Менеджеры", action: "amanat.manager_action" },
                        { name: "Курс Джесс", action: "amanat.jess_rate_action" },
                    ],
                },
                {
                    name: "Валютные операции",
                    items: [
                        { name: "Перевод", action: "amanat.transfer_action" },
                        { name: "Конвертации", action: "amanat.conversion_action" },
                        { name: "Валютный резерв", action: "amanat.reserve_action" },
                        { name: "Инвестиции", action: "amanat.investment_action" },
                    ],
                },
                {
                    name: "Вычислительные таблицы",
                    items: [
                        { name: "Ордер", action: "amanat.order_action" },
                        { name: "Контейнер", action: "amanat.money_action" },
                        { name: "Сверка", action: "amanat.reconciliation_action" },
                        { name: "Сверка файлы", action: "amanat.action_amanat_sverka_files" },
                        { name: "Касса файлы", action: "amanat.action_amanat_kassa_files" },
                    ],
                },
                {
                    name: "Выписки",
                    items: [
                        { name: "Выписки", action: "amanat.action_amanat_extracts" },
                        { name: "Выписка разнос", action: "amanat.extract_delivery_action" },
                    ],
                },
                {
                    name: "Калькуляторы",
                    items: [
                        { name: "Спред", action: "amanat.action_amanat_calculator_spread" },
                        { name: "Расчет добавка в $ Совком", action: "amanat.action_amanat_calculator_50_usd" },
                        { name: "Расчет добавка в $ для всех", action: "amanat.action_amanat_calculator_wizard" },
                        { name: "Калькулятор для фиксированного вознаграждения", action: "amanat.action_amanat_calculator_fixed_fee" },
                    ],
                },
            ];
        }

        if (this.state.userGroups.is_fin_manager) {
            return [
                {
                    name: "Валютные операции",
                    items: [
                        { name: "Перевод", action: "amanat.transfer_action" },
                        { name: "Конвертации", action: "amanat.conversion_action" },
                        { name: "Валютный резерв", action: "amanat.reserve_action" },
                        { name: "Инвестиции", action: "amanat.investment_action" },
                    ],
                },
                {
                    name: "Справочники",
                    items: [
                        { name: "Контрагенты", action: "amanat.contragent_action" },
                        { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                        { name: "Страны", action: "amanat.country_action" },
                        { name: "Плательщики", action: "amanat.payer_action" },
                        { name: "Менеджеры", action: "amanat.manager_action" },
                        { name: "Курс Джесс", action: "amanat.jess_rate_action" },
                    ],
                },
                {
                    name: "Вычислительные таблицы",
                    items: [
                        { name: "Ордер", action: "amanat.order_action" },
                        { name: "Контейнер", action: "amanat.money_action" },
                        { name: "Сверка", action: "amanat.reconciliation_action" },
                        { name: "Касса файлы", action: "amanat.action_amanat_kassa_files" },
                    ],
                },
                {
                    name: "Прайс листы",
                    items: [
                        { name: "Прайс лист партнеры", action: "amanat.price_list_partners_action" },
                        { name: "Прайс лист Плательщика", action: "amanat.price_list_payer_profit_action" },
                        { name: "Прайс лист Плательщика За проведение", action: "amanat.price_list_payer_carrying_out_action" },
                    ],
                },
                {
                    name: "Правила",
                    items: [
                        { name: "Правила Расход на операционную деятельность", action: "amanat.action_expense_rule" },
                        { name: "Правила Себестоимость денег", action: "amanat.action_money_cost_rule" },
                        { name: "Правила Платежка РФ", action: "amanat.action_payment_order_rule" },
                    ],
                },
                {
                    name: "Кассы",
                    items: [
                        { name: "Касса Иван", action: "amanat.kassa_ivan_action" },
                        { name: "Касса 2", action: "amanat.kassa_2_action" },
                        { name: "Касса 3", action: "amanat.kassa_3_action" },
                    ],
                },
                {
                    name: "Анализ",
                    items: [
                        { name: "Дашборд", action: "amanat.action_amanat_dashboard_js" },
                    ],
                },
                {
                    name: "Заявки",
                    action: "amanat.zayavka_action",
                    actionMethod: "openZayvaki",
                },
                {
                    name: "Калькуляторы",
                    items: [
                        { name: "Спред", action: "amanat.action_amanat_calculator_spread" },
                        { name: "Расчет добавка в $ Совком", action: "amanat.action_amanat_calculator_50_usd" },
                        { name: "Расчет добавка в $ для всех", action: "amanat.action_amanat_calculator_wizard" },
                        { name: "Калькулятор для фиксированного вознаграждения", action: "amanat.action_amanat_calculator_fixed_fee" },
                    ],
                },
            ];
        }
        
        if ((this.state.userGroups.is_manager || this.state.userGroups.is_senior_manager) && !this.state.userGroups.is_admin && !this.state.userGroups.is_transit_only) {
            return [
                {
                    name: "Справочники",
                    items: [
                        { name: "Контрагенты", action: "amanat.contragent_action" },
                        { name: "SWIFT Документы", action: "amanat.action_swift_document_upload" },
                        { name: "Страны", action: "amanat.country_action" },
                        { name: "Плательщики", action: "amanat.payer_action" },
                        { name: "Менеджеры", action: "amanat.manager_action" },
                    ],
                },
                {
                    name: "Заявки",
                    action: "amanat.zayavka_action",
                    actionMethod: "openZayvaki",
                },
                {
                    name: "Анализ",
                    items: [
                        { name: "Фикс заявка", action: "amanat.zayavka_fiks_dashboard_action_menu" },
                    ],
                },
                {
                    name: "Калькуляторы",
                    items: [
                        { name: "Спред", action: "amanat.action_amanat_calculator_spread" },
                        { name: "Расчет надбавка $ Совком", action: "amanat.action_amanat_calculator_50_usd" },
                        { name: "Расчет добавка в $ для всех", action: "amanat.action_amanat_calculator_wizard" },
                        { name: "Калькулятор для фиксированного вознаграждения", action: "amanat.action_amanat_calculator_fixed_fee" },
                    ],
                },
            ];
        }
        
        // Для остальных пользователей возвращаем полное меню
        return this.menuData;
    }

    handleMenuClick(menu, menu_index) {
        if (menu.items) {
            this.toggleMenu(menu_index);
        } else if (menu.actionMethod) {
            this[menu.actionMethod]();
            this.state.activeItem = menu.actionMethod;
            this.state.activeMainMenuIndex = menu_index;
        }
    }

    toggleSidebar() {
        this.state.isCollapsed = !this.state.isCollapsed;
        
        // Обновляем CSS переменную в зависимости от состояния
        if (this.state.isCollapsed) {
            document.documentElement.style.setProperty('--sidebar-width', '0px');
            document.body.classList.add('mk_sidebar_hidden');
        } else {
            document.documentElement.style.setProperty('--sidebar-width', this.state.sidebarWidth + 'px');
            document.body.classList.remove('mk_sidebar_hidden');
        }
    }

    toggleMenu(menu_index) {
        if (this.state.activeMenuIndex === menu_index) {
            this.state.activeMenuIndex = null;
        } else {
            this.state.activeMenuIndex = menu_index;
        }
    }

    openAction(actionName, menuIndex) {
        this.actionService.doAction(actionName, { additionalContext: { clear_breadcrumb: true } });
        this.state.activeItem = actionName;
        this.state.activeMainMenuIndex = menuIndex;
    }

    openAutomations() {
        this.actionService.doAction('amanat.action_automation_for_amanat', { additionalContext: { clear_breadcrumb: true } });
        this.state.activeItem = 'openAutomations';
    }

    openZayvaki() {
        this.actionService.doAction('amanat.zayavka_action', { additionalContext: { clear_breadcrumb: true } });
        this.state.activeItem = 'openZayvaki';
    }

    openLogs() {
        this.actionService.doAction('amanat.activity_action', { additionalContext: { clear_breadcrumb: true } });
        this.state.activeItem = 'openLogs';
    }

    // Методы для изменения размера сайдбара
    getSavedSidebarWidth() {
        const saved = localStorage.getItem('amanat_sidebar_width');
        return saved ? parseInt(saved) : 300; // Стандартная ширина 300px
    }

    saveSidebarWidth(width) {
        localStorage.setItem('amanat_sidebar_width', width.toString());
    }

    startResize(event) {
        event.preventDefault();
        this.isResizing = true;
        this.startX = event.clientX;
        this.startWidth = this.state.sidebarWidth;
        
        // Добавляем слушатели для перемещения мыши и отпускания кнопки
        document.addEventListener('mousemove', this.boundOnMouseMove);
        document.addEventListener('mouseup', this.boundStopResize);
        
        // Добавляем класс для изменения курсора
        document.body.classList.add('mk_sidebar_resizing');
    }

    onMouseMove(event) {
        if (!this.isResizing) return;
        
        const deltaX = event.clientX - this.startX;
        let newWidth = this.startWidth + deltaX;
        
        // Ограничиваем минимальную и максимальную ширину
        const minWidth = 200;
        const maxWidth = Math.min(600, window.innerWidth * 0.4); // Максимум 40% от ширины экрана или 600px
        
        newWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
        
        this.state.sidebarWidth = newWidth;
        // Обновляем CSS переменную для grid layout
        document.documentElement.style.setProperty('--sidebar-width', newWidth + 'px');
    }

    stopResize() {
        if (!this.isResizing) return;
        
        this.isResizing = false;
        
        // Удаляем слушатели событий
        document.removeEventListener('mousemove', this.boundOnMouseMove);
        document.removeEventListener('mouseup', this.boundStopResize);
        
        // Убираем класс изменения курсора
        document.body.classList.remove('mk_sidebar_resizing');
        
        // Сохраняем новую ширину
        this.saveSidebarWidth(this.state.sidebarWidth);
    }
}