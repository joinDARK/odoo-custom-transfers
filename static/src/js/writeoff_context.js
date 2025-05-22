/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

// Сохраняем оригинальный метод setup
const originalSetup = FormController.prototype.setup;

patch(FormController.prototype, {
    setup() {
        // вызываем оригинальный setup
        originalSetup.apply(this, arguments);

        // регистрируем хук, который выполнится до рендеринга формы
        async () => {
            const ctx = this.props.context || {};
            const activeId = ctx.active_id ?? ctx.activeId;
            console.log("activeId = ", activeId)
            if (activeId && this.props.resModel === 'amanat.writeoff') {
                console.log(
                    "Патчим investment_ids через onWillStart:",
                    activeId,
                    this.props.resModel
                );
                await this.model.update({
                    investment_ids: [[6, false, [activeId]]],
                });
            }
        };
    },
}, "amanat.WriteoffFormController");