/** @odoo-module **/

import { registry } from "@web/core/registry";

// Диагностический сервис для bus системы
const busDiagnosticService = {
    dependencies: ["bus_service"],
    
    start(env, { bus_service }) {
        console.log("🔍 BUS DIAGNOSTIC: Service starting...");
        
        // Глобальная функция для диагностики
        window.diagnoseBus = () => {
            console.log("🔍 BUS DIAGNOSTIC: Starting diagnosis...");
            console.log("🔍 Bus service object:", bus_service);
            console.log("🔍 Bus service methods:", Object.getOwnPropertyNames(bus_service));
            console.log("🔍 Bus service prototype:", Object.getOwnPropertyNames(Object.getPrototypeOf(bus_service)));
            
            // Проверяем доступные каналы
            if (bus_service.channels) {
                console.log("🔍 Current channels:", bus_service.channels);
            }
            
            // Проверяем текущую подписку
            const userId = window.odoo?.session_info?.uid || 2;
            const userChannel = `res.users,${userId}`;
            console.log(`🔍 Expected user channel: ${userChannel}`);
            
            // Пытаемся подписаться на канал разными способами
            try {
                if (typeof bus_service.addChannel === 'function') {
                    bus_service.addChannel(userChannel);
                    console.log("✅ addChannel method available and called");
                } else {
                    console.log("❌ addChannel method not available");
                }
            } catch (error) {
                console.log("❌ addChannel failed:", error);
            }
            
            console.log("🔍 BUS DIAGNOSTIC: Diagnosis completed");
        };
        
        // Подписываемся на ВСЕ bus события для диагностики
        try {
            bus_service.addEventListener("notification", ({ detail: notifications }) => {
                console.log("🔍 BUS DIAGNOSTIC: ANY notification received!");
                console.log("🔍 Notification count:", notifications.length);
                
                for (let i = 0; i < notifications.length; i++) {
                    const notification = notifications[i];
                    console.log(`🔍 Notification ${i + 1}:`, notification);
                    
                    // Пытаемся извлечь информацию разными способами
                    if (Array.isArray(notification)) {
                        console.log(`🔍 Array format: [${notification.join(', ')}]`);
                    } else if (typeof notification === 'object') {
                        console.log("🔍 Object keys:", Object.keys(notification));
                        console.log("🔍 Object values:", Object.values(notification));
                    }
                }
            });
            
            console.log("✅ Bus diagnostic listener added");
            
        } catch (error) {
            console.error("❌ Failed to add bus diagnostic listener:", error);
        }
        
        console.log("🔍 BUS DIAGNOSTIC: Service started");
        console.log("🔍 Use window.diagnoseBus() to run diagnosis");
        
        return {};
    }
};

// Регистрируем сервис
registry.category("services").add("bus_diagnostic", busDiagnosticService);

console.log("🔍 BUS DIAGNOSTIC: Service registered"); 