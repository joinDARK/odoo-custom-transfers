/** @odoo-module **/

import { registry } from "@web/core/registry";

const amanatRealTimeService = {
    dependencies: ["bus_service", "action"],
    start(env) {1234
        
        const busService = env.services.bus_service;
        busService.subscribe("my_channel", (message) => {
            if (['create', 'update', 'delete'].includes(message.type)) {
                const currentController = env.services.action.currentController;
                console.log("currentController", currentController);

                if (currentController && currentController.action) {
                    const resModel = currentController.action.res_model;
                    console.log("resModel", resModel);
                    console.log("resModel === message.model", resModel === message.model);
                    if (resModel === message.model) {
                        console.log("type", currentController.props.type);
                        if (currentController.props.type === 'list' || currentController.props.type === 'from') {
                            // currentController.reload();
                            console.log("Обнова модели нету бля!");
                        }
                    }
                }
            }
        });
        console.log("Amanat RealTime Service started");
        return {};
    },
};

registry.category("services").add("amanat_real_time", amanatRealTimeService);

export default amanatRealTimeService;