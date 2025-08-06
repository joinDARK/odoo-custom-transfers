/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { SelectionField } from "@web/views/fields/selection/selection_field";

export class SearchableSelectionField extends SelectionField {
    static template = "amanat.SearchableSelectionField";
    static components = {
        ...SelectionField.components,
        SelectMenu,
    };

    get selectMenuProps() {
        try {
            // Получаем опции правильным способом через родительский класс
            const options = this.options || [];
            if (!Array.isArray(options)) {
                console.warn('SearchableSelectionField: options is not an array', options);
                return null;
            }

            // Сохраняем порядок опций как в модели (по числам)
            const choices = options.map(([value, label]) => ({
                value,
                label,
            }));

            const currentValue = this.props.record.data[this.props.name] || false;

            return {
                choices,
                value: currentValue,
                searchable: true,
                searchPlaceholder: "Поиск...",
                onSelect: this.onSelect.bind(this),
                class: "",
                togglerClass: "o_input pe-3",
                required: true, // убираем крестик для очистки
                autoSort: false, // отключаем автосортировку, сохраняем порядок модели
            };
        } catch (error) {
            console.error('SearchableSelectionField: Error in selectMenuProps', error);
            return null;
        }
    }

    onSelect(value) {
        // SelectMenu передает напрямую значение, не объект
        if (value !== undefined) {
            this.props.record.update(
                { [this.props.name]: value },
                { save: this.props.autosave }
            );
        }
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    onChange(event) {
        // Для fallback select элемента - парсим как в оригинальном SelectionField
        const value = JSON.parse(event.target.value);
        this.props.record.update(
            { [this.props.name]: value },
            { save: this.props.autosave }
        );
    }

    get currentLabel() {
        try {
            const currentValue = this.props.record?.data?.[this.props.name];
            if (!currentValue) return this.props.placeholder || "";
            
            const options = this.options || [];
            if (!Array.isArray(options)) {
                return currentValue;
            }
            
            const option = options.find(([value]) => value === currentValue);
            return option ? option[1] : currentValue;
        } catch (error) {
            console.error('SearchableSelectionField: Error in currentLabel', error);
            return this.props.placeholder || "";
        }
    }
}

export const searchableSelectionField = {
    component: SearchableSelectionField,
    displayName: "Searchable Selection",
    supportedTypes: ["selection"],
    supportedOptions: [],
    supportedFieldTypes: ["selection"],
    useSubview: false,
};

registry.category("fields").add("searchable_selection", searchableSelectionField);