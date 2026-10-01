import re
import csv
import pandas as pd

# 1. Extract Categories
with open('Cafeteria Order Data.sql', 'rb') as f:
    f.seek(7563320)
    cat_chunk = f.read(45000).decode('utf-8', errors='ignore')

# Find INSERT INTO `categories`
match = re.search(r"INSERT INTO `categories` \([^)]+\) VALUES\s*([\s\S]+?);", cat_chunk)
if match:
    rows = []
    # Match tuple lines: (id, 'name', ...)
    for line in match.group(1).split('\n'):
        line = line.strip().rstrip(';,')
        if line.startswith('(') and line.endswith(')'):
            parts = line[1:-1].split(',', 6)
            if len(parts) >= 3:
                cat_id = parts[0].strip()
                cat_name = parts[1].strip().strip("'\"")
                is_active = parts[2].strip()
                rows.append((cat_id, cat_name, is_active))
    
    df_cat = pd.DataFrame(rows, columns=['category_id', 'category_name', 'is_active'])
    df_cat.to_csv('categories.csv', index=False)
    print(f"Extracted {len(df_cat)} categories -> categories.csv")
    print(df_cat.head(10))

# 2. Extract Dishes
with open('Cafeteria Order Data.sql', 'rb') as f:
    f.seek(13391831)
    dish_chunk = f.read(2500000).decode('utf-8', errors='ignore')

# Read dishes table schema and inserts
print("\nFinding dishes inserts...")
# Dish schema: id, name, dish_price, dish_status, category_id, branch_id...
dish_rows = []
for line in dish_chunk.split('\n'):
    line = line.strip().rstrip(';,')
    if not line.startswith('('):
        continue
    parts = line[1:].split(',', 15)
    if len(parts) >= 8:
        d_id = parts[0].strip()
        d_name = parts[1].strip().strip("'\"")
        d_price = parts[2].strip()
        d_status = parts[3].strip()
        d_branch = parts[7].strip()
        dish_rows.append((d_id, d_name, d_price, d_status, d_branch))

if dish_rows:
    df_dish = pd.DataFrame(dish_rows, columns=['dish_id', 'dish_name', 'price', 'status', 'branch_id'])
    df_dish.to_csv('dishes.csv', index=False)
    print(f"Extracted {len(df_dish)} dishes -> dishes.csv")
    print(df_dish.head(10))
