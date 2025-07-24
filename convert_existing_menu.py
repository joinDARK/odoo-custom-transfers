#!/usr/bin/env python3
"""
Конвертация существующего меню ID 138 для казначея
"""

import xmlrpc.client

# Настройки подключения к Odoo
url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin'

def convert_existing_menu():
    try:
        # Подключение к Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Ошибка аутентификации")
            return
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print("🔧 КОНВЕРТИРУЕМ СУЩЕСТВУЮЩЕЕ МЕНЮ ID 138...")
        
        # Получаем ID группы казначея
        treasurer_group = models.execute_kw(db, uid, password, 'res.groups', 'search_read',
            [[['name', '=', 'Казначей']]], 
            {'fields': ['id']})
        
        if not treasurer_group:
            print("❌ Группа казначея не найдена!")
            return
            
        treasurer_group_id = treasurer_group[0]['id']
        print(f"✅ ID группы казначея: {treasurer_group_id}")
        
        # Читаем текущее состояние меню ID 138
        menu_138 = models.execute_kw(db, uid, password, 'ir.ui.menu', 'read',
            [[138]], {'fields': ['name', 'action', 'groups_id', 'sequence']})
        
        if menu_138:
            menu = menu_138[0]
            print(f"\n📋 ТЕКУЩЕЕ СОСТОЯНИЕ меню ID 138:")
            print(f"   Название: {menu['name']}")
            print(f"   Действие: {menu['action']}")
            print(f"   Группы: {menu['groups_id']}")
            print(f"   Приоритет: {menu['sequence']}")
        
        # ПЛАН А: Изменить меню 138 на action-507 и добавить казначея
        print(f"\n🔧 ПЛАН А: Конвертируем меню 138 в меню казначея...")
        
        # Обновляем меню 138
        update_data = {
            'action': 'ir.actions.act_window,507',  # Меняем на action-507
            'groups_id': [(6, 0, [treasurer_group_id])],  # Только казначей
            'sequence': 1  # Высший приоритет
        }
        
        models.execute_kw(db, uid, password, 'ir.ui.menu', 'write',
            [[138], update_data])
        
        print(f"   ✅ Меню 138 обновлено")
        
        # Проверяем результат
        updated_menu = models.execute_kw(db, uid, password, 'ir.ui.menu', 'read',
            [[138]], {'fields': ['name', 'action', 'groups_id', 'sequence']})
        
        if updated_menu:
            menu = updated_menu[0]
            print(f"\n✅ ОБНОВЛЕННОЕ СОСТОЯНИЕ меню ID 138:")
            print(f"   Название: {menu['name']}")
            print(f"   Действие: {menu['action']}")
            print(f"   Приоритет: {menu['sequence']}")
            
            if menu['groups_id']:
                groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [menu['groups_id']], {'fields': ['name']})
                group_names = [g['name'] for g in groups]
                print(f"   Группы: {', '.join(group_names)}")
        
        # Финальная проверка доступности
        print(f"\n🔍 ФИНАЛЬНАЯ ПРОВЕРКА доступности казначею...")
        
        child_menus = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [[['parent_id', '=', 122]]], 
            {'fields': ['id', 'name', 'action', 'groups_id'], 
             'order': 'sequence ASC, id ASC'})
        
        treasurer_accessible = []
        
        for menu in child_menus:
            is_accessible = False
            if menu['groups_id']:
                is_accessible = treasurer_group_id in menu['groups_id']
            else:
                is_accessible = True
            
            if is_accessible:
                treasurer_accessible.append(menu)
                action_info = menu['action'] or 'Нет действия'
                print(f"  ✅ ID {menu['id']}: {menu['name']} → {action_info}")
        
        print(f"\n🎯 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        print(f"   Дочерних меню доступных казначею: {len(treasurer_accessible)}")
        
        if len(treasurer_accessible) == 1:
            menu = treasurer_accessible[0]
            action_parts = menu['action'].split(',') if menu['action'] else ['', 'None']
            action_id = action_parts[1] if len(action_parts) == 2 else 'None'
            
            if action_id == '507':
                print(f"   🎉 УСПЕХ! Казначей видит только меню с action-507")
                print(f"\n🎊 ПРОБЛЕМА ПОЛНОСТЬЮ РЕШЕНА!")
                print(f"\n📋 ИНСТРУКЦИИ ДЛЯ ИЛЬЗИРЫ:")
                print(f"   1. Закрыть ВСЕ вкладки браузера")
                print(f"   2. Очистить кэш (Ctrl+Shift+Del)")
                print(f"   3. Перезапустить браузер")
                print(f"   4. Залогиниться заново")
                print(f"   5. Нажать 'Заявки' → откроется action-507 с ограниченными полями!")
            else:
                print(f"   ⚠️  Меню ведет к action-{action_id}")
        else:
            print(f"   ⚠️  Проблема: казначей видит {len(treasurer_accessible)} меню")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    convert_existing_menu() 