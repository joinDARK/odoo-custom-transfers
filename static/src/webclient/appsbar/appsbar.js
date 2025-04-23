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
                ],
            },
            {
                name: "Остальное",
                items: [
                    { name: "Диапазоны", action: "amanat.ranges_action" },
                    { name: "Курсы к доллару", action: "amanat.rates_action" },
                    { name: "Платежи", action: "amanat.payment_action" },
                    { name: "Выписка разнос", action: "amanat.extract_delivery_action" },
                    { name: "Выписки", action: "amanat.action_amanat_extracts" },
                    { name: "Период", action: "amanat.action_amanat_period" },
                    { name: "Сверка файлы", action: "amanat.action_amanat_sverka_files" },
                    { name: "Списания", action: "amanat.writeoff_action" },
                    { name: "Контрагенты", action: "amanat.contragent_action" },
                    { name: "Плательщики", action: "amanat.payer_action" },
                    { name: "Кошелек", action: "amanat.wallet_action" },
                    { name: "Страны", action: "amanat.country_action" },
                    { name: "Менеджеры", action: "amanat.manager_action" },
                    { name: "Заявки", action: "amanat.zayavka_action" },
                    { name: "Касса Иван", action: "amanat.kassa_ivan_action" },
                    { name: "Касса 2", action: "amanat.kassa_2_action" },
                    { name: "Касса 3", action: "amanat.kassa_3_action" },
                    { name: "Прайс лист партнеры", action: "amanat.price_list_partners_action" },
                    { name: "Прайс лист Плательщика", action: "amanat.price_list_payer_profit_action" },
                    { name: "Золото сделка", action: "amanat.gold_deal_action" },
                    { name: "Партнеры золото", action: "amanat.partner_gold_action" },
                ],
            },
            {
                name: "Автоматизации",
                actionMethod: "openAutomations",
            },
            {
                name: "Логи",
                actionMethod: "openLogs",
            },
        ];

        this.state = useState({
            isCollapsed: false,
            activeMenuIndex: null,
            isAmanat: false,
            appName: '',
        });

        const refreshMenuState = () => {
            const currentApp = this.appMenuService.getCurrentApp();
            if (currentApp) {
                this.state.appName = currentApp.name;
                this.state.isAmanat = (currentApp.name === 'ТДК');
                this.state.activeMenuIndex = null;
            }
        };
        refreshMenuState();

        this.env.bus.addEventListener('MENUS:APP-CHANGED', refreshMenuState);
        onWillUnmount(() => {
            this.env.bus.removeEventListener('MENUS:APP-CHANGED', refreshMenuState);
        });

        if (this.companyService.currentCompany.has_appsbar_image) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'appbar_image',
                id: this.companyService.currentCompany.id,
            });
        }
    }

    // Клик по пункту: либо раскрыть подпункты, либо вызвать метод
    handleMenuClick(menu, menu_index) {
        if (menu.items) {
            // Есть подпункты, значит сворачиваем/разворачиваем
            this.toggleMenu(menu_index);
        } else if (menu.actionMethod) {
            // Вызываем метод по имени (например, "openAutomations")
            this[menu.actionMethod]();
        }
    }

    // Сворачивание боковой панели (не задействовано в шаблоне по умолчанию)
    toggleSidebar() {
        this.state.isCollapsed = !this.state.isCollapsed;
    }

    // Раскрытие / сворачивание подпунктов
    toggleMenu(menu_index) {
        if (this.state.activeMenuIndex === menu_index) {
            this.state.activeMenuIndex = null;
        } else {
            this.state.activeMenuIndex = menu_index;
        }
    }

    openAction(actionName) {
        console.log(actionName);
        this.actionService.doAction(actionName, { additionalContext: { clear_breadcrumb: true } });
    }

    openAutomations() {
        this.actionService.doAction('amanat.action_automation_for_amanat', { additionalContext: { clear_breadcrumb: true } });
    }

    openLogs() {
        this.actionService.doAction('amanat.activity_action', { additionalContext: { clear_breadcrumb: true } });
    }
}
