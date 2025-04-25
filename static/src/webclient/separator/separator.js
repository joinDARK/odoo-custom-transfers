/** @odoo-module */

import { FloatField } from "@web/views/fields/float_field";
import { registry } from "@web/core/registry";

console.log("Separator widget loaded");

class Separator extends FloatField {
    parseValue(input) {
        console.log("Separator widget loaded");
        if (typeof input !== 'string') {
            input = String(input);
        }
        input = input.trim();

        var dotIndex = input.lastIndexOf('.');
        var commaIndex = input.lastIndexOf(',');

        var decimalSeparator;
        if (dotIndex > commaIndex) {
            decimalSeparator = '.';
        } else if (commaIndex > dotIndex) {
            decimalSeparator = ',';
        } else {
            decimalSeparator = null;
        }

        if (decimalSeparator) {
            var parts = input.split(decimalSeparator);
            var integerPart = parts.slice(0, -1).join('').replace(/[\.,]/g, '');
            var decimalPart = parts[parts.length - 1];
            input = integerPart + '.' + decimalPart;
        } else {
            input = input.replace(/[\.,]/g, '');
        }

        var result = parseFloat(input);
        if (isNaN(result)) {
            throw new Error("'" + input + "' is not a correct float");
        }
        return result;
    }

    onInput(event) {
        console.log("Separator widget loaded");
        const value = event.target.value;
        console.log("input");
        try {
            const parsedValue = this.parseValue(value);
            this.props.update(parsedValue);
        } catch (e) {
            console.error(e.message);
        }
    }
}

registry.category("fields").add("separator", CustomFloatField);