/** @odoo-module **/

import { registry } from "@web/core/registry";

// Обработчик для вызова JavaScript функций из Python
registry.category("actions").add("call_js_function", (env, action) => {
    const { params } = action;
    const functionName = params.function_name;
    const args = params.args || [];
    
    // Проверяем, что функция существует в window
    if (window[functionName] && typeof window[functionName] === 'function') {
        // Вызываем функцию с переданными аргументами
        window[functionName](...args);
    } else {
        console.error(`JavaScript function ${functionName} not found`);
        env.services.notification.add(
            `Функция ${functionName} не найдена`,
            { type: "danger" }
        );
    }
}); 