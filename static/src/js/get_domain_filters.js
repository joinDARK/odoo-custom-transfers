/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

console.debug("[PATCH] Загружается патч для ListController.onClickCreate");

patch(ListController.prototype, {
    async onClickCreate() {
        console.debug('[onClickCreate] МЕТОД ВЫЗВАН! Начинаем обработку создания записи');

        // Проверяем, что это нужная модель
        const allowedModels = ['amanat.transfer', 'amanat.reserve', 'amanat.conversion', 'amanat.investment'];
        const currentModel = this.props.resModel || this.model?.resModel;

        console.debug('[onClickCreate] Текущая модель:', currentModel);
        console.debug('[onClickCreate] Разрешенные модели:', allowedModels);

        if (!currentModel || !allowedModels.includes(currentModel)) {
            console.debug('[onClickCreate] Модель не в списке разрешенных, используем стандартное поведение');
            return super.onClickCreate();
        }

        console.debug('[onClickCreate] Модель разрешена, применяем кастомную логику');
        // Получаем активные фильтры из searchModel
        let domainSearchItems = [];

        console.debug("[onClickCreate] this.model.env == ", this.model.env);

        let activeDomain = [];
        let parsedFilters = {};

        try {
            // Проверяем разные способы получения searchItems
            if (this.model.env?.searchModel) {
                domainSearchItems = this.model.env.searchModel.searchDomain;
                activeDomain = domainSearchItems; // Это уже готовый домен
            } else {
                console.debug("[onClickCreate] searchModel не найден в this.model.env");
            }

            console.debug("[onClickCreate] domainSearchItems == ", domainSearchItems);

            // Парсим домен и извлекаем значения для дефолтных полей
            if (Array.isArray(activeDomain) && activeDomain.length > 0) {
                // Ищем простые фильтры вида [field, operator, value]
                for (let i = 0; i < activeDomain.length; i++) {
                    const item = activeDomain[i];

                    // Пропускаем логические операторы
                    if (typeof item === 'string' && (item === '&' || item === '|' || item === '!')) {
                        continue;
                    }

                    // Обрабатываем массивы условий
                    if (Array.isArray(item) && item.length === 3) {
                        const [field, operator, value] = item;

                        // Динамически сохраняем значения для всех полей с операторами = или in
                        if (operator === '=' || operator === 'in') {
                            let processedValue = value;

                            // Для оператора 'in' берем первый элемент массива
                            if (operator === 'in' && Array.isArray(value) && value.length > 0) {
                                processedValue = value[0];
                            }

                            // Создаем ключ для дефолтного значения
                            const defaultKey = `default_${field}`;
                            parsedFilters[defaultKey] = processedValue;

                            console.debug(`[onClickCreate] Извлечено из фильтра: ${field} ${operator} ${value} -> ${defaultKey} = ${processedValue}`);
                        }
                    }
                }
            }

            console.debug("[onClickCreate] parsedFilters == ", parsedFilters);

        } catch (error) {
            console.error("[onClickCreate] Ошибка при получении фильтров:", error);
        }
        
        // Модифицируем контекст props напрямую
        Object.assign(this.props.context, parsedFilters);

        console.debug("[onClickCreate] Модифицированный контекст props:", this.props.context);
        console.debug("[onClickCreate] Вызываем super.onClickCreate");

        const result = super.onClickCreate();
        console.debug("[onClickCreate] Результат вызова super.onClickCreate:", result);

        return result;
    }
});

console.debug("[PATCH] Патч для ListController.onClickCreate успешно применен");