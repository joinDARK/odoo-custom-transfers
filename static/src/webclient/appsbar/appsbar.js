/** @odoo-module **/

import { url } from '@web/core/utils/urls';
import { useState } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { Component, onWillUnmount, reactive } from '@odoo/owl';

export class AppsBar extends Component {
    static template = 'amanat.AppsBar';
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.companyService = useService('company');
        this.appMenuService = useService('app_menu');

        const currentApp = this.appMenuService.getCurrentApp();
        this.state = useState({
            isAmanat: currentApp ? currentApp.name === 'Amanat' : false,
            appName: currentApp ? currentApp.name : ''
        });

        const refreshMenuState = () => {
            const currentApp = this.appMenuService.getCurrentApp();
            if (currentApp) {
                this.state.appName = currentApp.name;
                this.state.isAmanat = currentApp.name === 'Amanat';
            }
            console.log("Обновлено состояние:", this.state);
        };

        refreshMenuState(); // Начальный вызов

        this.env.bus.addEventListener('MENUS:APP-CHANGED', refreshMenuState);
        onWillUnmount(() => {
            this.env.bus.removeEventListener('MENUS:APP-CHANGED', refreshMenuState);
        });

        // Если нужно загружать картинку:
        if (this.companyService.currentCompany.has_appsbar_image) {
            this.sidebarImageUrl = url('/web/image', {
                model: 'res.company',
                field: 'appbar_image',
                id: this.companyService.currentCompany.id,
            });
        }
    }

    openAutomations() {
        this.actionService.doAction('amanat.action_automation_for_amanat');
    }

    openLogs() {
        this.actionService.doAction('amanat.activity_action');
    }
}
