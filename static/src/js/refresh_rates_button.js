/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Client action для обновления курсов без перезагрузки страницы
 * Использует тот же подход что и аналитический дашборд - прямые ORM вызовы
 */
registry.category("actions").add("refresh_rates_action", async (env, action) => {
    const orm = env.services.orm;
    const notification = env.services.notification;
    
    // Выводим сообщения в консоль если есть
    if (action.params && action.params.console_messages) {
        console.group("🔄 Обновление курсов валют");
        
        action.params.console_messages.forEach(message => {
            if (message.includes('❌') || message.includes('💥')) {
                console.error(message);
            } else if (message.includes('⚠️')) {
                console.warn(message);
            } else if (message.includes('✅') || message.includes('🎉')) {
                console.info(message);
            } else {
                console.log(message);
            }
        });
        
        console.groupEnd();
    }
    
    // Показываем уведомление
    if (action.params) {
        notification.add(
            action.params.message || "Операция выполнена",
            {
                title: action.params.title || "Информация",
                type: action.params.type || "info",
                sticky: action.params.sticky || false,
            }
        );
    }
    
    // 🚀 Обновляем форму без перезагрузки (улучшенный метод для форм Odoo)
    if (action.params && action.params.type === 'success' && action.params.updated_rates) {
        console.info("🔄 Обновляем данные формы без перезагрузки...");
        
        try {
            // Получаем текущий контроллер
            if (env.services && env.services.action) {
                const currentController = env.services.action.currentController;
                if (currentController && currentController.props && currentController.props.resId) {
                    const resId = currentController.props.resId;
                    
                    console.info(`🔄 Обновляем поля в форме для записи ${resId}...`);
                    
                    // Получаем обновленные курсы из параметров action
                    const updatedRates = action.params.updated_rates[resId];
                    if (updatedRates) {
                        // Находим и обновляем поля курсов в DOM (улучшенная версия для разных типов полей)
                        const updateField = (fieldName, value) => {
                            // Попробуем найти поле несколькими способами
                            let fieldElement = document.querySelector(`[name="${fieldName}"] input`);
                            let isInputField = true;
                            
                            if (!fieldElement) {
                                // Попробуем найти как span или div для readonly полей
                                fieldElement = document.querySelector(`[name="${fieldName}"] span, [name="${fieldName}"] .o_field_widget`);
                                isInputField = false;
                            }
                            
                            if (!fieldElement) {
                                // Последняя попытка - найти любой элемент с именем поля
                                fieldElement = document.querySelector(`[name="${fieldName}"]`);
                                isInputField = fieldElement && fieldElement.tagName === 'INPUT';
                            }
                            
                            if (fieldElement) {
                                const displayValue = value || '';
                                
                                if (isInputField) {
                                    fieldElement.value = displayValue;
                                    fieldElement.dispatchEvent(new Event('change', { bubbles: true }));
                                    fieldElement.dispatchEvent(new Event('input', { bubbles: true }));
                                } else {
                                    fieldElement.textContent = displayValue;
                                    // Для текстовых полей также попробуем обновить innerHTML
                                    if (fieldElement.innerHTML !== undefined) {
                                        fieldElement.innerHTML = displayValue;
                                    }
                                }
                                
                                // Специальная обработка для best_rate_name
                                if (fieldName === 'best_rate_name') {
                                    console.info(`🎯 BEST_RATE_NAME обновлено: "${displayValue}" (элемент: ${fieldElement.tagName})`);
                                } else {
                                    console.info(`✅ Поле ${fieldName} обновлено: ${displayValue}`);
                                }
                                return true;
                            } else {
                                console.warn(`⚠️ Не удалось найти элемент для поля ${fieldName}`);
                                return false;
                            }
                        };
                        
                        // Обновляем поля курсов
                        if (updatedRates.cb_rate !== null) {
                            updateField('cb_rate', updatedRates.cb_rate);
                        }
                        if (updatedRates.investing_rate !== null) {
                            updateField('investing_rate', updatedRates.investing_rate);
                        }
                        
                        // 🚀 ПРИОРИТЕТНО обновляем "Лучший курс Наименование" (important!)
                        if (updatedRates.best_rate_name !== undefined) {
                            console.info(`🎯 Обновляем ПРИОРИТЕТНОЕ поле best_rate_name: "${updatedRates.best_rate_name}"`);
                            const success = updateField('best_rate_name', updatedRates.best_rate_name);
                            if (!success) {
                                console.error(`❌ НЕ УДАЛОСЬ обновить best_rate_name!`);
                            }
                        }
                        
                        // 🚀 Обновляем остальные пересчитанные зависимые поля (как в дашбордах)
                        const dependentFields = [
                            'best_rate', 
                            'effective_rate',
                            'our_client_reward',
                            'client_reward',
                            'non_our_client_reward',
                            'total_client',
                            'partner_post_conversion_rate'
                        ];
                        
                        dependentFields.forEach(fieldName => {
                            if (updatedRates[fieldName] !== undefined && updatedRates[fieldName] !== null) {
                                const success = updateField(fieldName, updatedRates[fieldName]);
                                if (success) {
                                    console.info(`✅ Зависимое поле ${fieldName} обновлено: ${updatedRates[fieldName]}`);
                                } else {
                                    console.warn(`⚠️ Не удалось обновить поле ${fieldName}`);
                                }
                            }
                        });
                        
                        // Альтернативный способ: триггерим reload модели если DOM обновление не сработало
                        setTimeout(async () => {
                            if (currentController.model && currentController.model.root) {
                                try {
                                    await currentController.model.root.load();
                                    console.info("✅ Модель формы дополнительно обновлена");
                                } catch (modelError) {
                                    console.warn("⚠️ Не удалось обновить модель:", modelError);
                                }
                            }
                        }, 100);
                        
                        // Подсчитываем количество обновленных полей
                        const updatedFieldsCount = dependentFields.filter(field =>
                            updatedRates[field] !== undefined && updatedRates[field] !== null
                        ).length + 
                        (updatedRates.cb_rate !== null ? 1 : 0) + 
                        (updatedRates.investing_rate !== null ? 1 : 0) +
                        (updatedRates.best_rate_name !== undefined ? 1 : 0); // Учитываем best_rate_name
                        
                        notification.add(`Курсы обновлены, пересчитано ${updatedFieldsCount} полей (включая "Лучший курс Наименование")`, {
                            type: "success",
                            sticky: false,
                        });
                    } else {
                        console.warn("⚠️ Нет данных об обновленных курсах");
                    }
                } else {
                    console.warn("⚠️ Не удалось получить ID текущей записи");
                }
            } else {
                console.warn("⚠️ Action service недоступен");
            }
        } catch (error) {
            console.error("❌ Ошибка при обновлении формы:", error);
            console.info("💡 Данные обновлены на сервере, попробуйте обновить страницу");
            
            // Fallback к перезагрузке страницы
            notification.add("Данные обновлены. Обновите страницу для отображения", {
                type: "warning",
                sticky: true,
            });
        }
    } else {
        console.info("⚠️ Курсы не обновлены или были ошибки - автообновление отключено");
    }
    
    return Promise.resolve();
});