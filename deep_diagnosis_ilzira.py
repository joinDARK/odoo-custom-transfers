#!/usr/bin/env python3
"""
Глубокая диагностика всего доступного для Ильзиры (казначея)
"""

import xmlrpc.client

# Настройки подключения к Odoo
url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin'

def deep_diagnosis_ilzira():
    try:
        # Подключение к Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Ошибка аутентификации")
            return
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print("🕵️ ГЛУБОКАЯ ДИАГНОСТИКА ДЛЯ ИЛЬЗИРЫ...")
        
        # 1. Проверяем пользователя Ильзира
        print(f"\n1️⃣ ПОЛЬЗОВАТЕЛЬ ИЛЬЗИРА:")
        
        ilzira = models.execute_kw(db, uid, password, 'res.users', 'search_read',
            [[['login', '=', 'ilzira@tdk.local']]], 
            {'fields': ['id', 'name', 'login', 'groups_id']})
        
        if not ilzira:
            print("❌ Пользователь не найден!")
            return
            
        ilzira_user = ilzira[0]
        print(f"✅ ID: {ilzira_user['id']}, Имя: {ilzira_user['name']}")
        
        # Получаем группы пользователя
        if ilzira_user['groups_id']:
            groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                [ilzira_user['groups_id']], {'fields': ['name']})
            group_names = [g['name'] for g in groups]
            print(f"✅ Группы: {', '.join(group_names)}")
            
            has_treasurer = 'Казначей' in group_names
            print(f"✅ Является казначеем: {'Да' if has_treasurer else 'НЕТ'}")
        else:
            print("❌ Нет групп!")
            return
        
        # 2. Ищем ВСЕ меню доступные Ильзире
        print(f"\n2️⃣ ВСЕ МЕНЮ ДОСТУПНЫЕ ИЛЬЗИРЕ:")
        
        # Получаем ID группы казначея
        treasurer_group = models.execute_kw(db, uid, password, 'res.groups', 'search_read',
            [[['name', '=', 'Казначей']]], {'fields': ['id']})
        
        if not treasurer_group:
            print("❌ Группа казначея не найдена!")
            return
            
        treasurer_group_id = treasurer_group[0]['id']
        
        # Ищем все меню для казначея И общедоступные
        all_menus = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [['|', ['groups_id', '=', False], ['groups_id', 'in', [treasurer_group_id]]]], 
            {'fields': ['id', 'name', 'parent_id', 'action', 'sequence'], 
             'order': 'parent_id, sequence ASC, id ASC'})
        
        print(f"Найдено {len(all_menus)} доступных меню:")
        
        zayavka_menus = []
        action_198_menus = []
        
        for menu in all_menus:
            parent_info = menu['parent_id'][1] if menu['parent_id'] else 'Корень'
            action_info = menu['action'] or 'Нет действия'
            
            print(f"  ID {menu['id']}: {menu['name']}")
            print(f"    Родитель: {parent_info}")
            print(f"    Действие: {action_info}")
            print()
            
            # Собираем меню со словом "Заявки"
            if 'Заявки' in menu['name']:
                zayavka_menus.append(menu)
                
            # Собираем меню с action-198
            if menu['action'] and '198' in menu['action']:
                action_198_menus.append(menu)
        
        # 3. Анализ меню "Заявки"
        print(f"\n3️⃣ АНАЛИЗ МЕНЮ 'ЗАЯВКИ':")
        print(f"Найдено {len(zayavka_menus)} меню со словом 'Заявки':")
        
        for menu in zayavka_menus:
            action_parts = menu['action'].split(',') if menu['action'] else ['', 'None']
            action_id = action_parts[1] if len(action_parts) == 2 else 'None'
            
            print(f"  ID {menu['id']}: {menu['name']} → action-{action_id}")
            print(f"    Приоритет: {menu['sequence']}")
            
            if action_id == '507':
                print(f"    ✅ ПРАВИЛЬНОЕ меню казначея")
            elif action_id == '195':
                print(f"    ❌ ПРОБЛЕМНОЕ меню (старое)")
            elif action_id == '198':
                print(f"    🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА! Это action-198!")
        
        # 4. Анализ action-198
        print(f"\n4️⃣ АНАЛИЗ ACTION-198 (КУДА РЕДИРЕКТИТ):")
        print(f"Найдено {len(action_198_menus)} меню с action-198:")
        
        for menu in action_198_menus:
            parent_info = menu['parent_id'][1] if menu['parent_id'] else 'Корень'
            print(f"  ID {menu['id']}: {menu['name']}")
            print(f"    Родитель: {parent_info}")
            print(f"    🚨 ДОСТУПНО КАЗНАЧЕЮ! Это источник проблемы!")
        
        # 5. Проверяем action-507
        print(f"\n5️⃣ ПРОВЕРКА ACTION-507:")
        
        action_507 = models.execute_kw(db, uid, password, 'ir.actions.act_window', 'search_read',
            [[['id', '=', 507]]], 
            {'fields': ['name', 'res_model', 'view_mode', 'groups_id']})
        
        if action_507:
            action = action_507[0]
            print(f"✅ Action-507 найден: {action['name']}")
            print(f"✅ Модель: {action['res_model']}")
            print(f"✅ Режимы: {action['view_mode']}")
            
            if action['groups_id']:
                groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [action['groups_id']], {'fields': ['name']})
                group_names = [g['name'] for g in groups]
                print(f"✅ Группы action-507: {', '.join(group_names)}")
                
                if 'Казначей' in group_names:
                    print(f"✅ Action-507 доступен казначею")
                else:
                    print(f"❌ Action-507 НЕ доступен казначею!")
            else:
                print(f"✅ Action-507 доступен всем")
        else:
            print(f"❌ Action-507 НЕ найден!")
        
        # 6. Проверяем action-198  
        print(f"\n6️⃣ ПРОВЕРКА ACTION-198:")
        
        action_198 = models.execute_kw(db, uid, password, 'ir.actions.act_window', 'search_read',
            [[['id', '=', 198]]], 
            {'fields': ['name', 'res_model', 'view_mode', 'groups_id']})
        
        if action_198:
            action = action_198[0]
            print(f"🚨 Action-198 найден: {action['name']}")
            print(f"🚨 Модель: {action['res_model']}")
            
            if action['groups_id']:
                groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [action['groups_id']], {'fields': ['name']})
                group_names = [g['name'] for g in groups]
                print(f"🚨 Группы action-198: {', '.join(group_names)}")
                
                if 'Казначей' in group_names:
                    print(f"🚨 ПРОБЛЕМА! Action-198 доступен казначею!")
                else:
                    print(f"✅ Action-198 скрыт от казначея")
            else:
                print(f"🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА! Action-198 доступен ВСЕМ!")
        
        # 7. Рекомендации
        print(f"\n7️⃣ ПЛАН ИСПРАВЛЕНИЯ:")
        
        if action_198_menus:
            print(f"🔧 НЕМЕДЛЕННО убрать казначея из меню с action-198:")
            for menu in action_198_menus:
                print(f"   - Меню ID {menu['id']}: {menu['name']}")
        
        if action_198 and (not action_198[0]['groups_id']):
            print(f"🔧 ОГРАНИЧИТЬ доступ к action-198 (сейчас доступен всем)")
        
        print(f"🔧 ПРИНУДИТЕЛЬНО очистить кэш браузера и сервера")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    deep_diagnosis_ilzira() 