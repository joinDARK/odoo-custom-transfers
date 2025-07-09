/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

// Регистрируем команду swift
commandRegistry.add("swift", {
    help: _t("Получить информацию о SWIFT/BIC коде. Применение: /swift <БИК_КОД> [<НОМЕР_ЗАЯВКИ>]"),
    methodName: "execute_command_swift",
    channel_types: ["chat", "channel", "group"],
}); 