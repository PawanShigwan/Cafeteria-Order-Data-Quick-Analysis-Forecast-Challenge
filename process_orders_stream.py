import time
import os
import csv
from collections import defaultdict

print("Starting high-performance streaming analysis of orders...", flush=True)
t0 = time.time()

# Daily aggregates: key (date_str, branch_id)
daily_stats = defaultdict(lambda: {
    'total_orders': 0,
    'paid_orders': 0,
    'cancelled_orders': 0,
    'total_revenue': 0.0,
    'total_tax': 0.0,
    'total_discount': 0.0,
    'pos_orders': 0,
    'app_orders': 0,
    'sok_orders': 0,
    'other_channel_orders': 0,
    'cash_orders': 0,
    'qr_orders': 0,
    'upi_orders': 0,
    'card_orders': 0,
    'wallet_orders': 0,
    'unique_users': set()
})

branch_totals = defaultdict(lambda: {
    'total_orders': 0,
    'paid_orders': 0,
    'cancelled_orders': 0,
    'total_revenue': 0.0,
    'min_date': '9999-99-99',
    'max_date': '0000-00-00',
    'channels': defaultdict(int),
    'payments': defaultdict(int)
})

hourly_stats = defaultdict(lambda: defaultdict(int)) # (branch_id, hour) -> count

ORDERS_START_OFFSET = 91541411

processed_lines = 0
valid_orders = 0

with open('Cafeteria Order Data.sql', 'r', encoding='utf-8', errors='ignore') as f:
    f.seek(ORDERS_START_OFFSET)
    
    for line in f:
        # Check termination condition when order_details table begins
        if line.startswith('CREATE TABLE `order_details`') or line.startswith('INSERT INTO `order_details`'):
            print(f"Reached order_details table at line {processed_lines:,}. Ending orders scan.", flush=True)
            break
            
        if not line.startswith('('):
            continue
            
        processed_lines += 1
        
        # Split up to 32 items
        parts = line[1:380].split(',', 32)
        if len(parts) < 31:
            continue
            
        order_id = parts[0].strip()
        user_id = parts[2].strip()
        order_status = parts[3].strip()
        order_date_raw = parts[6].strip().strip("'\"")
        branch_id = parts[8].strip()
        order_through = parts[12].strip().strip("'\"").lower()
        sub_total_raw = parts[13].strip()
        tax_amount_raw = parts[14].strip()
        discount_amount_raw = parts[18].strip()
        payment_mode_raw = parts[19].strip().strip("'\"").lower()
        grand_total_raw = parts[28].strip()
        paid_or_cancel = parts[30].strip().strip("'\"").lower()
        
        # Fast date check
        if len(order_date_raw) >= 10:
            date_str = order_date_raw[:10]
            try:
                hour = int(order_date_raw[11:13])
            except:
                hour = 12
        else:
            continue
            
        try:
            grand_total = float(grand_total_raw)
        except:
            grand_total = 0.0
            
        try:
            tax_amount = float(tax_amount_raw)
        except:
            tax_amount = 0.0
            
        try:
            discount_amount = float(discount_amount_raw)
        except:
            discount_amount = 0.0
            
        valid_orders += 1
        
        # Update daily stats
        key = (date_str, branch_id)
        d = daily_stats[key]
        d['total_orders'] += 1
        
        b = branch_totals[branch_id]
        b['total_orders'] += 1
        if date_str < b['min_date']:
            b['min_date'] = date_str
        if date_str > b['max_date']:
            b['max_date'] = date_str
            
        is_paid = ('paid' in paid_or_cancel) or (order_status == '3')
        is_cancel = ('cancel' in paid_or_cancel) or (order_status == '2') or ('fail' in paid_or_cancel)
        
        if is_paid:
            d['paid_orders'] += 1
            d['total_revenue'] += grand_total
            d['total_tax'] += tax_amount
            d['total_discount'] += discount_amount
            b['paid_orders'] += 1
            b['total_revenue'] += grand_total
        elif is_cancel:
            d['cancelled_orders'] += 1
            b['cancelled_orders'] += 1
            
        # Channel
        if 'pos' in order_through:
            d['pos_orders'] += 1
            b['channels']['pos'] += 1
        elif 'app' in order_through or 'mobile' in order_through:
            d['app_orders'] += 1
            b['channels']['mobile_app'] += 1
        elif 'sok' in order_through or 'kiosk' in order_through:
            d['sok_orders'] += 1
            b['channels']['kiosk_sok'] += 1
        else:
            d['other_channel_orders'] += 1
            b['channels'][order_through or 'unknown'] += 1
            
        # Payment mode
        if 'cash' in payment_mode_raw:
            d['cash_orders'] += 1
            b['payments']['cash'] += 1
        elif 'qr' in payment_mode_raw:
            d['qr_orders'] += 1
            b['payments']['qr'] += 1
        elif 'upi' in payment_mode_raw:
            d['upi_orders'] += 1
            b['payments']['upi'] += 1
        elif 'card' in payment_mode_raw:
            d['card_orders'] += 1
            b['payments']['card'] += 1
        elif 'paytm' in payment_mode_raw or 'cca' in payment_mode_raw or 'wallet' in payment_mode_raw:
            d['wallet_orders'] += 1
            b['payments']['wallet_pg'] += 1
        else:
            b['payments']['other'] += 1
            
        if user_id and user_id != 'NULL':
            d['unique_users'].add(user_id)
            
        hourly_stats[branch_id][hour] += 1
        
        if processed_lines % 500000 == 0:
            elapsed = time.time() - t0
            rate = processed_lines / elapsed if elapsed > 0 else 0
            print(f"Processed {processed_lines:,} lines ({valid_orders:,} valid orders) in {elapsed:.1f}s ({rate:,.0f} rows/s)...", flush=True)

dt = time.time() - t0
print(f"\nProcessing complete! Processed {processed_lines:,} lines ({valid_orders:,} valid orders) in {dt:.1f}s ({processed_lines/dt:,.0f} rows/s)", flush=True)

# Export daily_branch_summary.csv
print("\nExporting daily_branch_summary.csv...", flush=True)
with open('daily_branch_summary.csv', 'w', newline='', encoding='utf-8') as f_out:
    writer = csv.writer(f_out)
    writer.writerow([
        'date', 'branch_id', 'total_orders', 'paid_orders', 'cancelled_orders',
        'total_revenue', 'total_tax', 'total_discount', 'avg_order_value',
        'pos_orders', 'app_orders', 'sok_orders', 'other_channel_orders',
        'cash_orders', 'qr_orders', 'upi_orders', 'card_orders', 'wallet_orders',
        'unique_customers'
    ])
    
    for (date_str, branch_id), stats in sorted(daily_stats.items()):
        paid = stats['paid_orders']
        rev = stats['total_revenue']
        aov = round(rev / paid, 2) if paid > 0 else 0.0
        writer.writerow([
            date_str, branch_id, stats['total_orders'], paid, stats['cancelled_orders'],
            round(rev, 2), round(stats['total_tax'], 2), round(stats['total_discount'], 2), aov,
            stats['pos_orders'], stats['app_orders'], stats['sok_orders'], stats['other_channel_orders'],
            stats['cash_orders'], stats['qr_orders'], stats['upi_orders'], stats['card_orders'], stats['wallet_orders'],
            len(stats['unique_users'])
        ])

print("Saved daily_branch_summary.csv!", flush=True)

# Print branch summary
print("\n=== BRANCH SUMMARY OVERVIEW ===", flush=True)
for b_id, b_info in sorted(branch_totals.items(), key=lambda x: x[1]['total_orders'], reverse=True):
    print(f"Branch ID: {b_id:<3} | Orders: {b_info['total_orders']:>9,} | Paid: {b_info['paid_orders']:>9,} | Cancel: {b_info['cancelled_orders']:>6,} | Revenue: Rs.{b_info['total_revenue']:>12,.2f} | Dates: {b_info['min_date']} to {b_info['max_date']}", flush=True)

# Export hourly breakdown
print("\nExporting hourly_branch_summary.csv...", flush=True)
with open('hourly_branch_summary.csv', 'w', newline='', encoding='utf-8') as f_out:
    writer = csv.writer(f_out)
    writer.writerow(['branch_id', 'hour', 'order_count'])
    for b_id in sorted(hourly_stats.keys()):
        for h in range(24):
            writer.writerow([b_id, h, hourly_stats[b_id][h]])
print("Saved hourly_branch_summary.csv!", flush=True)

print("\nAll done successfully!", flush=True)
