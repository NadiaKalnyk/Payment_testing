# ==============================================================================
# 1. ЗАВАНТАЖЕННЯ ДАНИХ ТА ЗМІННІ
# ==============================================================================

stripe_data = load_csv('hw_stripe_export.csv')
merchant_data = load_csv('hw_merchant_db.csv')

discrepancies = []  # Зберігаємо знайдені розбіжності

# Карта статусів для зведення до одного вигляду
STATUS_MAP = {
    "paid": "succeeded",
    "succeeded": "succeeded",
    "refunded": "refunded",
    "authorized": "authorized",
    "failed": "failed"
}

# ==============================================================================
# 2. ПЕРЕВІРКА НА ДУБЛІКАТИ (DUPLICATE)
# ==============================================================================

# Шукаємо повтори ID всередині кожного файлу
for tx_id, count in count_occurrences(merchant_data, key='charge_id').items():
    if count > 1:
        add_issue(tx_id, type='Duplicate', desc=f'Дублікат у БД: {count} рази', severity='P1')

for tx_id, count in count_occurrences(stripe_data, key='id').items():
    if count > 1:
        add_issue(tx_id, type='Duplicate', desc=f'Дублікат у Stripe: {count} рази', severity='P1')

# ==============================================================================
# 3. ПОШУК ВІДСУТНІХ ТРАНЗАКЦІЙ (MISSING)
# ==============================================================================

stripe_ids = get_ids(stripe_data, key='id')
merchant_ids = get_ids(merchant_data, key='charge_id')

# Є в Stripe, але немає в БД
for tx_id in (stripe_ids - merchant_ids):
    add_issue(
        tx_id,
        type='Missing',
        desc='Є в Stripe, але немає в БД',
        severity='P0')

# Є в БД, але немає в Stripe
for tx_id in (merchant_ids - stripe_ids):
    add_issue(
        tx_id,
        type='Missing',
        desc='Є в БД, але немає в Stripe',
        severity='P1')

# ==============================================================================
# 4. ПОРІВНЯННЯ ТРАНЗАКЦІЙ, ЯКІ Є В ОБОХ СИСТЕМАХ
# ==============================================================================

common_ids = stripe_ids
AND
merchant_ids

for tx_id in common_ids:
    stripe_row = get_row(stripe_data, id=tx_id)
    merchant_row = get_row(merchant_data, id=tx_id)

    # --------------------------------------------------------------------------
    # А) Перевірка суми (Amount mismatch)
    # Stripe: долари ("65.00") -> переводимо в центи (* 100)
    # Враховуємо повернення коштів (Amount Refunded)
    # --------------------------------------------------------------------------
    stripe_net_dollars = stripe_row['Amount'] - stripe_row['Amount Refunded']
    stripe_cents = stripe_net_dollars * 100
    merchant_cents = merchant_row['amount_cents']

    if stripe_cents != merchant_cents:
        add_issue(
            tx_id,
            type='Amount mismatch',
            desc=f'Stripe: {stripe_cents} ц vs БД: {merchant_cents} ц',
            severity='P0'
        )

    # --------------------------------------------------------------------------
    # Б) Перевірка статусу (Status mismatch)
    # --------------------------------------------------------------------------
    stripe_status = STATUS_MAP.get(stripe_row['Status'].lower())

    # Якщо повернуто 100% суми, вважаємо статус "refunded"
    if stripe_row['Amount Refunded'] == stripe_row['Amount'] and stripe_row['Amount'] > 0:
        stripe_status = "refunded"

    merchant_status = merchant_row['status'].lower()

    if stripe_status != merchant_status:
        severity = 'P0' if stripe_status == 'refunded' else 'P1'
        add_issue(
            tx_id,
            type='Status mismatch',
            desc=f'Stripe: {stripe_status} vs БД: {merchant_status}',
            severity=severity
        )

    # --------------------------------------------------------------------------
    # В) Перевірка дати (Timestamp > 1 день)
    # --------------------------------------------------------------------------
    days_diff = get_days_difference(stripe_row['Created date'], merchant_row['created_at'])

    if days_diff > 1:
        add_issue(
            tx_id,
            type='Timestamp',
            desc=f'Різниця в даті: {days_diff} днів',
            severity='P2'
        )

# ==============================================================================
# 5. ВІДПРАВКА АЛЕРТІВ ТА ЗБЕРЕЖЕННЯ ЗВІТУ
# ==============================================================================

if discrepancies:
    save_to_csv('reconciliation_report.csv', discrepancies)

    # Блокуючі помилки (P0 / P1) надсилаємо терміново
    critical_issues = filter_by_severity(discrepancies, ['P0', 'P1'])
    if critical_issues:
        send_slack_alert(
            channel='#payments-critical-alerts',
            data=critical_issues)

    # Другорядні попередження (P2) надсилаємо в окремий лог
    warning_issues = filter_by_severity(discrepancies, ['P2'])
    if warning_issues:
        send_slack_alert(
            channel='#payments-reconciliation-log',
            data=warning_issues)