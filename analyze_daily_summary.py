import pandas as pd
import numpy as np

df = pd.read_csv('daily_branch_summary.csv')
print("=== DAILY BRANCH SUMMARY SHAPE ===")
print(df.shape)
print("\nColumns:", df.columns.tolist())

# Filter to main branches: 1, 2, 4, 9
main_branches = df[df['branch_id'].isin([1, 2, 4, 9])]
print("\n=== SUMMARY BY BRANCH ===")
grouped = main_branches.groupby('branch_id').agg({
    'date': ['count', 'min', 'max'],
    'total_orders': ['sum', 'mean', 'std', 'min', 'max'],
    'total_revenue': ['sum', 'mean'],
    'avg_order_value': 'mean'
})
print(grouped)

# Check Branch 1 daily distribution
b1 = df[df['branch_id'] == 1].copy()
b1['date'] = pd.to_datetime(b1['date'])
b1 = b1.sort_values('date')
b1['dow'] = b1['date'].dt.day_name()
print("\n=== BRANCH 1 (NIRLON KNOWLEDGE PARK) DAY OF WEEK PATTERN ===")
print(b1.groupby('dow')['total_orders'].agg(['count', 'mean', 'median', 'min', 'max']).reindex([
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
]))

# Check Branch 2 daily distribution
b2 = df[df['branch_id'] == 2].copy()
b2['date'] = pd.to_datetime(b2['date'])
b2 = b2.sort_values('date')
b2['dow'] = b2['date'].dt.day_name()
print("\n=== BRANCH 2 (EMBASSY TECH VILLAGE) DAY OF WEEK PATTERN ===")
print(b2.groupby('dow')['total_orders'].agg(['count', 'mean', 'median', 'min', 'max']).reindex([
    'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
]))
