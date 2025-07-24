/** @odoo-module */

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AmanatWelcomeScreen extends Component {
    static template = "amanat_welcome_template";

    setup() {
        this.actionService = useService("action");
        this.env.config.setDisplayName("Добро пожаловать в ТДК");
    }

    /**
     * Открывает указанное действие
     */
    async openAction(actionXmlId) {
        try {
            await this.actionService.doAction(actionXmlId);
        } catch (error) {
            console.error("Error opening action:", error);
        }
    }

    /**
     * Получает текущую дату для отображения
     */
    getCurrentDate() {
        return new Date().toLocaleDateString('ru-RU', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    /**
     * Получает приветствие в зависимости от времени суток
     */
    getTimeBasedGreeting() {
        const hour = new Date().getHours();
        if (hour < 12) {
            return "Доброе утро!";
        } else if (hour < 18) {
            return "Добрый день!";
        } else {
            return "Добрый вечер!";
        }
    }
}

// Регистрируем client action
registry.category("actions").add("amanat_welcome", AmanatWelcomeScreen); 