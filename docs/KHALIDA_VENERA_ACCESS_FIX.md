# Исправление доступа для Халиды и Венеры

## Проблема
После первоначальной настройки прав доступа к вкладке "Анализ" у **Халиды** и **Венеры** доступы не изменились.

## Причина проблемы
Пользователям были предоставлены права только к модели `amanat.analytics_dashboard`, но аналитический дашборд для работы требует доступа к основным данным системы для получения и расчета аналитической информации.

## Решение
Добавлены дополнительные права доступа (только чтение) к следующим моделям:

### Для Венеры (group_amanat_venera_analytics):
- `amanat.zayavka` - заявки
- `amanat.transfer` - переводы  
- `amanat.order` - ордера
- `amanat.money` - денежные контейнеры
- `amanat.contragent` - контрагенты
- `amanat.rates` - курсы валют
- `amanat.manager` - менеджеры
- `amanat.reconciliation` - сверки

### Для Халиды (group_amanat_khalida_analytics):
- `amanat.zayavka` - заявки  
- `amanat.transfer` - переводы
- `amanat.order` - ордера
- `amanat.money` - денежные контейнеры
- `amanat.contragent` - контрагенты
- `amanat.rates` - курсы валют
- `amanat.manager` - менеджеры
- `amanat.reconciliation` - сверки

### Для Веры финдир (group_amanat_vera_findir):
- Те же самые права доступа для консистентности

## Внесенные изменения в файл security/ir.model.access.csv
```csv
# Доступ к основным моделям для аналитики - Венера
access_amanat_zayavka_venera_analytics,amanat.zayavka,model_amanat_zayavka,group_amanat_venera_analytics,1,0,0,0
access_amanat_transfer_venera_analytics,amanat.transfer,model_amanat_transfer,group_amanat_venera_analytics,1,0,0,0
access_amanat_order_venera_analytics,amanat.order,model_amanat_order,group_amanat_venera_analytics,1,0,0,0
access_amanat_money_venera_analytics,amanat.money,model_amanat_money,group_amanat_venera_analytics,1,0,0,0
access_amanat_contragent_venera_analytics,amanat.contragent,model_amanat_contragent,group_amanat_venera_analytics,1,0,0,0
access_amanat_rates_venera_analytics,amanat.rates,model_amanat_rates,group_amanat_venera_analytics,1,0,0,0
access_amanat_manager_venera_analytics,amanat.manager,model_amanat_manager,group_amanat_venera_analytics,1,0,0,0
access_amanat_reconciliation_venera_analytics,amanat.reconciliation,model_amanat_reconciliation,group_amanat_venera_analytics,1,0,0,0

# Доступ к основным моделям для аналитики - Халида
access_amanat_zayavka_khalida_analytics,amanat.zayavka,model_amanat_zayavka,group_amanat_khalida_analytics,1,0,0,0
access_amanat_transfer_khalida_analytics,amanat.transfer,model_amanat_transfer,group_amanat_khalida_analytics,1,0,0,0
access_amanat_order_khalida_analytics,amanat.order,model_amanat_order,group_amanat_khalida_analytics,1,0,0,0
access_amanat_money_khalida_analytics,amanat.money,model_amanat_money,group_amanat_khalida_analytics,1,0,0,0
access_amanat_contragent_khalida_analytics,amanat.contragent,model_amanat_contragent,group_amanat_khalida_analytics,1,0,0,0
access_amanat_rates_khalida_analytics,amanat.rates,model_amanat_rates,group_amanat_khalida_analytics,1,0,0,0
access_amanat_manager_khalida_analytics,amanat.manager,model_amanat_manager,group_amanat_khalida_analytics,1,0,0,0
access_amanat_reconciliation_khalida_analytics,amanat.reconciliation,model_amanat_reconciliation,group_amanat_khalida_analytics,1,0,0,0

# Доступ к основным моделям для аналитики - Вера финдир
access_amanat_zayavka_vera_findir,amanat.zayavka,model_amanat_zayavka,group_amanat_vera_findir,1,0,0,0
access_amanat_transfer_vera_findir,amanat.transfer,model_amanat_transfer,group_amanat_vera_findir,1,0,0,0
access_amanat_order_vera_findir,amanat.order,model_amanat_order,group_amanat_vera_findir,1,0,0,0
access_amanat_money_vera_findir,amanat.money,model_amanat_money,group_amanat_vera_findir,1,0,0,0
access_amanat_contragent_vera_findir,amanat.contragent,model_amanat_contragent,group_amanat_vera_findir,1,0,0,0
access_amanat_rates_vera_findir,amanat.rates,model_amanat_rates,group_amanat_vera_findir,1,0,0,0
access_amanat_manager_vera_findir,amanat.manager,model_amanat_manager,group_amanat_vera_findir,1,0,0,0
access_amanat_reconciliation_vera_findir,amanat.reconciliation,model_amanat_reconciliation,group_amanat_vera_findir,1,0,0,0
```

## Инструкции по применению исправления

### 1. Обновление модуля
После внесения изменений необходимо обновить модуль Amanat:
```bash
# Через интерфейс Odoo: Приложения -> Amanat -> Обновить
# Или через командную строку:
./odoo-bin -u amanat -d your_database_name
```

### 2. Проверка доступа
После обновления модуля:

1. **Халида** должна увидеть пункт меню "Анализ" и иметь возможность:
   - Открыть аналитический дашборд
   - Просматривать данные по заявкам, переводам, курсам
   - Генерировать аналитические отчеты

2. **Венера** должна получить такой же доступ к аналитике

3. **Вера финдир** - доступ должен работать без изменений

### 3. Проверка функциональности
- Убедитесь, что дашборд "Анализ" загружается без ошибок
- Проверьте, что отображаются данные за разные периоды
- Убедитесь, что графики и метрики работают корректно

### 4. Устранение неполадок
Если проблемы остаются:

1. **Проверьте назначение групп пользователям** в интерфейсе администратора
2. **Очистите кэш браузера** и обновите страницу
3. **Проверьте логи Odoo** на наличие ошибок доступа
4. **Убедитесь**, что пользователи имеют базовую группу `base.group_user`

## Права доступа (только чтение)
Все добавленные права настроены как **только чтение** (1,0,0,0), что означает:
- ✅ Чтение данных - разрешено
- ❌ Запись данных - запрещено  
- ❌ Создание записей - запрещено
- ❌ Удаление записей - запрещено

Это обеспечивает безопасность системы, позволяя пользователям только просматривать аналитические данные.

## Дата исправления
**Дата**: September 11, 2025
**Статус**: Исправление применено
