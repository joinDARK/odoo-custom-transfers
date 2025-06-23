/** @odoo-module **/

import { registry } from "@web/core/registry";

// Простой отладочный сервис
const debugRealtimeService = {
    dependencies: ["bus_service"],
    
    start(env, { bus_service }) {
        console.log("🔧 DEBUG: Real-time debug service starting...");
        
        // Подписываемся на все bus сообщения для отладки  
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            console.log("🔧 DEBUG: Bus notification received:", notifications);
            console.log("🔧 DEBUG: Total notifications count:", notifications.length);
            console.log("🔧 DEBUG: Raw notifications structure:", JSON.stringify(notifications, null, 2));
            
            for (const notification of notifications) {
                console.log("🔧 DEBUG: Processing notification:", notification);
                
                // Проверяем разные возможные структуры
                let type, payload;
                
                if (notification.type) {
                    type = notification.type;
                    payload = notification.payload;
                } else if (Array.isArray(notification) && notification.length >= 2) {
                    console.log("🔧 DEBUG: Array notification format detected");
                    type = notification[1];
                    payload = notification[2];
                } else if (notification.message) {
                    console.log("🔧 DEBUG: Message property detected");
                    type = notification.message.type;
                    payload = notification.message.payload;
                } else {
                    console.log("🔧 DEBUG: Unknown notification format");
                }
                
                console.log("🔧 DEBUG: Extracted type:", type);
                console.log("🔧 DEBUG: Extracted payload:", payload);
                
                if (type === "amanat_realtime_update") {
                    console.log("🎯 DEBUG: Amanat realtime update detected!");
                    console.log("🎯 DEBUG: Update data:", payload);
                } else {
                    console.log("🔧 DEBUG: Other notification type:", type);
                }
            }
        });
        
        // Также выводим информацию о текущем пользователе
        console.log("🔧 DEBUG: Current user info from session:", {
            user_id: window.odoo?.session_info?.uid,
            user_name: window.odoo?.session_info?.user_name,
            session_info: window.odoo?.session_info
        });
        
        console.log("🔧 DEBUG: Real-time debug service started successfully");
        
        return {
            logMessage: (message) => {
                console.log("🔧 DEBUG:", message);
            }
        };
    }
};

// Регистрируем отладочный сервис
registry.category("services").add("debug_realtime", debugRealtimeService);

console.log("🔧 DEBUG: Debug realtime service registered"); 