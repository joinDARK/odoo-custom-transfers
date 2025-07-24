/** @odoo-module */

import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart, onWillUnmount } from '@odoo/owl';
import { patch } from '@web/core/utils/patch';
import { WebClient } from '@web/webclient/webclient';

/**
 * Патч для WebClient для управления видимостью o_menu_sections
 * в зависимости от текущего приложения
 */
patch(WebClient.prototype, {
    setup() {
        super.setup();
        this.appMenuService = useService('app_menu');
        
        // Функция для управления видимостью menu sections
        const toggleMenuSections = () => {
            const currentApp = this.appMenuService.getCurrentApp();
            const menuSections = document.querySelector('.o_menu_sections');
            
            if (currentApp && menuSections) {
                if (currentApp.name === 'ТДК') {
                    // В модуле Amanat скрываем menu sections
                    menuSections.style.display = 'none';
                    document.body.classList.add('amanat_module_active');
                } else {
                    // В других модулях показываем menu sections (по дефолту)
                    menuSections.style.display = '';
                    document.body.classList.remove('amanat_module_active');
                }
            }
        };

        // Инициализация при запуске
        onWillStart(async () => {
            // Ждем небольшую задержку чтобы DOM элементы успели загрузиться
            setTimeout(toggleMenuSections, 100);
        });

        // Слушаем изменения приложения
        const handleAppChanged = () => {
            // Используем небольшую задержку, чтобы дать время DOM обновиться
            setTimeout(toggleMenuSections, 50);
        };

        this.env.bus.addEventListener('MENUS:APP-CHANGED', handleAppChanged);
        
        // Также слушаем общие изменения в роутере
        if (this.env.services && this.env.services.router) {
            const originalPush = this.env.services.router.push;
            this.env.services.router.push = (...args) => {
                const result = originalPush.apply(this.env.services.router, args);
                setTimeout(toggleMenuSections, 100);
                return result;
            };
        }
        
        // Наблюдатель за изменениями DOM для случаев динамической загрузки
        const observer = new MutationObserver((mutations) => {
            let shouldCheck = false;
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    const addedNodes = Array.from(mutation.addedNodes);
                    if (addedNodes.some(node => 
                        node.nodeType === Node.ELEMENT_NODE && 
                        (node.classList?.contains('o_menu_sections') || 
                         node.querySelector?.('.o_menu_sections'))
                    )) {
                        shouldCheck = true;
                    }
                }
            });
            if (shouldCheck) {
                setTimeout(toggleMenuSections, 10);
            }
        });

        // Начинаем наблюдение за изменениями в body
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        onWillUnmount(() => {
            this.env.bus.removeEventListener('MENUS:APP-CHANGED', handleAppChanged);
            observer.disconnect();
        });
    }
}); 