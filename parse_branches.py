import re
import pandas as pd

with open('Cafeteria Order Data.sql', 'rb') as f:
    f.seek(1437894)
    content = f.read(15000).decode('utf-8', errors='ignore')

# Find INSERT INTO `branches`
insert_match = re.search(r"INSERT INTO `branches` \([^)]+\) VALUES\s*([\s\S]+?);", content)
if insert_match:
    vals_str = insert_match.group(1).strip()
    # parse tuples
    rows = []
    # Match each row (...),
    for m in re.finditer(r"\(([^)]+)\)[,;]?", vals_str):
        raw = m.group(1)
        # Split by comma considering quotes
        parts = []
        cur = []
        in_quote = False
        quote_char = ''
        for char in raw:
            if char in ("'", '"') and not in_quote:
                in_quote = True
                quote_char = char
                cur.append(char)
            elif char == quote_char and in_quote:
                in_quote = False
                cur.append(char)
            elif char == ',' and not in_quote:
                parts.append("".join(cur).strip().strip("'\""))
                cur = []
            else:
                cur.append(char)
        if cur:
            parts.append("".join(cur).strip().strip("'\""))
        rows.append(parts)
    
    cols = ['id', 'name', 'branch_code', 'branch_merchant_code', 'branch_manager', 'invoice_prefix', 'contact_number', 'is_active', 'company_has_region_id', 'company_id', 'is_pos', 'is_sok', 'is_qrcode', 'is_mobile_ordering', 'is_table_room', 'country_id', 'state_id', 'city_id', 'license_id', 'license_no', 'gst_no', 'tax_ids', 'discount_ids', 'is_for_app', 'dining_page_link', 'created_at', 'updated_at']
    df = pd.DataFrame(rows, columns=cols[:len(rows[0])])
    print(df[['id', 'name', 'branch_code', 'branch_manager', 'city_id', 'is_active', 'created_at']])
    df.to_csv('branches.csv', index=False)
    print("Saved branches.csv successfully!")
