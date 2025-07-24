#!/usr/bin/env python3
"""
Скрипт для отладки созданного меню казначея
"""

import xmlrpc.client

# Настройки подключения к Odoo
url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin'

def debug_created_menu():
    try:
        # Подключение к Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Ошибка аутентификации")
            return
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print("🔍 Отладка созданного меню...")
        
        # Проверяем меню ID 326
        menu_326 = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [[['id', '=', 326]]], 
            {'fields': ['id', 'name', 'parent_id', 'action', 'groups_id', 'sequence', 'active']})
        
        if menu_326:
            menu = menu_326[0]
            print(f"✅ Меню ID 326 найдено:")
            print(f"   Название: {menu['name']}")
            print(f"   Родитель: {menu['parent_id']}")
            print(f"   Действие: {menu['action']}")
            print(f"   Приоритет: {menu['sequence']}")
            print(f"   Активно: {menu['active']}")
            
            if menu['groups_id']:
                groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [menu['groups_id']], {'fields': ['name']})
                group_names = [g['name'] for g in groups]
                print(f"   Группы: {', '.join(group_names)}")
        else:
            print(f"❌ Меню ID 326 НЕ найдено!")
        
        # Ищем ВСЕ меню казначея
        print(f"\n🔍 Поиск ВСЕХ меню для группы Казначей:")
        
        # Получаем ID группы казначея
        treasurer_group = models.execute_kw(db, uid, password, 'res.groups', 'search_read',
            [[['name', '=', 'Казначей']]], 
            {'fields': ['id']})
        
        if treasurer_group:
            treasurer_group_id = treasurer_group[0]['id']
            
            # Ищем все меню этой группы
            treasurer_menus = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
                [[['groups_id', 'in', [treasurer_group_id]]]], 
                {'fields': ['id', 'name', 'parent_id', 'action', 'sequence', 'active'], 
                 'order': 'id DESC'})  # Сортируем по убыванию чтобы новые были первыми
            
            print(f"Найдено {len(treasurer_menus)} меню для казначея:")
            
            for menu in treasurer_menus:
                parent_info = menu['parent_id'][1] if menu['parent_id'] else 'Корень'
                action_info = menu['action'] or 'Нет действия'
                status = "✅ Активно" if menu['active'] else "❌ Неактивно"
                
                print(f"  ID {menu['id']}: {menu['name']}")
                print(f"    Родитель: {parent_info}")
                print(f"    Действие: {action_info}")
                print(f"    {status}")
                print()
        
        # Принудительно проверяем дочерние меню ID 122 еще раз  
        print(f"🔍 ПРИНУДИТЕЛЬНАЯ ПРОВЕРКА дочерних меню ID 122:")
        
        all_children = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [[['parent_id', '=', 122]]], 
            {'fields': ['id', 'name', 'action', 'active'], 
             'order': 'id DESC'})
        
        print(f"Всего дочерних меню: {len(all_children)}")
        
        for menu in all_children:
            action_info = menu['action'] or 'Нет действия'
            status = "✅ Активно" if menu['active'] else "❌ Неактивно"
            
            print(f"  ID {menu['id']}: {menu['name']} → {action_info} | {status}")
            
            if menu['id'] == 326:
                print(f"    🎯 ЭТО НАШЕ СОЗДАННОЕ МЕНЮ!")
        
        # Если меню не отображается, попробуем принудительно активировать
        if menu_326 and not menu_326[0]['active']:
            print(f"\n🔧 Меню неактивно, активируем...")
            models.execute_kw(db, uid, password, 'ir.ui.menu', 'write',
                [[326], {'active': True}])
            print(f"✅ Меню активировано")
        
        print(f"\n💡 РЕКОМЕНДАЦИЯ:")
        print(f"   1. Перезапустить Odoo сервер (очистить кэш)")
        print(f"   2. Очистить кэш браузера")
        print(f"   3. Перелогиниться")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    debug_created_menu() 