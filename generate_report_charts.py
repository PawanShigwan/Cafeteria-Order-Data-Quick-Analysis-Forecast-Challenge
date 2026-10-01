import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Style configuration
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 300

ARTIFACT_DIR = r"C:\Users\HP\.gemini\antigravity-ide\brain\88e0ee83-187a-4c66-935a-e04b67468f15"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# 1. Load Data
df_branch_master = pd.read_csv('PowerBI_Branch_Master.csv')
df_daily_b1 = pd.read_csv('PowerBI_Branch1_Daily_Forecast.csv')
df_hourly = pd.read_csv('PowerBI_Hourly_Distribution.csv')
df_eval = pd.read_csv('PowerBI_Model_Evaluation.csv')
df_forecast = pd.read_csv('PowerBI_7Day_Forecast_Results.csv')
df_cp = pd.read_csv('PowerBI_Channel_Payment_Mix.csv')

# CHART 1: Enterprise Branch Revenue & Order Distribution
fig, ax1 = plt.subplots(figsize=(10, 5.5))
top_branches = df_branch_master.head(5).copy()
x = np.arange(len(top_branches))
width = 0.38

color1 = '#1E3A8A' # Deep Navy
color2 = '#0D9488' # Teal

rects1 = ax1.bar(x - width/2, top_branches['total_orders'] / 1e6, width, label='Total Orders (Millions)', color=color1, alpha=0.9, edgecolor='none')
ax1.set_ylabel('Total Orders (Millions)', color=color1, fontsize=11, fontweight='bold')
ax1.tick_params(axis='y', labelcolor=color1)
ax1.set_xticks(x)
ax1.set_xticklabels(top_branches['branch_name'], rotation=15, ha='right', fontsize=9.5, fontweight='bold')

ax2 = ax1.twinx()
rects2 = ax2.bar(x + width/2, top_branches['total_revenue'] / 1e7, width, label='Gross Revenue (₹ Crores)', color=color2, alpha=0.9, edgecolor='none')
ax2.set_ylabel('Gross Revenue (₹ Crores)', color=color2, fontsize=11, fontweight='bold')
ax2.tick_params(axis='y', labelcolor=color2)
ax2.grid(False)

plt.title('Cafeteria Portfolio: Top Branches by Order Volume & Revenue (FY 2024-25)', fontsize=13, fontweight='bold', pad=15)
fig.tight_layout()
fig.savefig('chart_1_branch_comparison.png', dpi=300)
fig.savefig(os.path.join(ARTIFACT_DIR, 'chart_1_branch_comparison.png'), dpi=300)
plt.close()
print("Saved Chart 1: Branch Comparison")

# CHART 2: Day-of-Week Seasonality (Nirlon Knowledge Park)
b1_actuals = df_daily_b1[df_daily_b1['data_type'] == 'Actual'].copy()
b1_actuals['date'] = pd.to_datetime(b1_actuals['date'])
b1_actuals['dow'] = b1_actuals['date'].dt.day_name()
order_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

dow_stats = b1_actuals.groupby('dow')['total_orders'].agg(['mean', 'median', 'std']).reindex(order_days)

fig, ax = plt.subplots(figsize=(9, 5))
bars = ax.bar(dow_stats.index, dow_stats['mean'], color=['#3B82F6' if d not in ['Saturday', 'Sunday'] else '#94A3B8' for d in dow_stats.index], edgecolor='#1E293B', linewidth=1, alpha=0.85)
ax.errorbar(dow_stats.index, dow_stats['mean'], yerr=dow_stats['std'], fmt='none', ecolor='#1E293B', capsize=5, elinewidth=1.5)

for bar in bars:
    yval = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2.0, yval + 350, f"{int(round(yval)):,}", ha='center', va='bottom', fontsize=9, fontweight='bold')

ax.set_ylabel('Average Daily Orders', fontsize=11, fontweight='bold')
ax.set_title('Nirlon Knowledge Park: Corporate Day-of-Week Order Seasonality', fontsize=12.5, fontweight='bold', pad=15)
ax.set_ylim(0, 12500)
fig.tight_layout()
fig.savefig('chart_2_dow_seasonality.png', dpi=300)
fig.savefig(os.path.join(ARTIFACT_DIR, 'chart_2_dow_seasonality.png'), dpi=300)
plt.close()
print("Saved Chart 2: DOW Seasonality")

# CHART 3: Hourly Demand Distribution Across Operating Day
fig, ax = plt.subplots(figsize=(10, 5))
b1_hourly = df_hourly[df_hourly['branch_id'] == 1].sort_values('hour')

ax.plot(b1_hourly['hour'], b1_hourly['order_count'] / 1000, marker='o', linewidth=2.5, color='#4F46E5', markersize=6)
ax.fill_between(b1_hourly['hour'], b1_hourly['order_count'] / 1000, color='#6366F1', alpha=0.2)

# Annotate peaks
ax.axvspan(12, 14.5, color='#FBBF24', alpha=0.25, label='Lunch Peak (12 PM - 2:30 PM)')
ax.axvspan(16, 18, color='#34D399', alpha=0.25, label='Snacks Peak (4 PM - 6 PM)')
ax.set_xticks(range(0, 24))
ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, fontsize=8.5)
ax.set_xlabel('Hour of Day', fontsize=11, fontweight='bold')
ax.set_ylabel('Orders (Thousands)', fontsize=11, fontweight='bold')
ax.set_title('Nirlon Knowledge Park: 24-Hour Intraday Order Distribution', fontsize=12.5, fontweight='bold', pad=15)
ax.legend(loc='upper right', frameon=True)
fig.tight_layout()
fig.savefig('chart_3_hourly_demand.png', dpi=300)
fig.savefig(os.path.join(ARTIFACT_DIR, 'chart_3_hourly_demand.png'), dpi=300)
plt.close()
print("Saved Chart 3: Hourly Demand")

# CHART 4: Forecasting Model Benchmark (Validation Accuracy)
fig, ax = plt.subplots(figsize=(9.5, 4.8))
eval_sorted = df_eval.sort_values('MAPE (%)', ascending=True).copy()
y_pos = np.arange(len(eval_sorted))
colors = ['#10B981' if i == 0 else ('#3B82F6' if i < 4 else '#94A3B8') for i in range(len(eval_sorted))]

bars = ax.barh(y_pos, eval_sorted['MAPE (%)'], color=colors, height=0.65)
ax.set_yticks(y_pos)
ax.set_yticklabels(eval_sorted['Model'], fontsize=9.5, fontweight='bold')
ax.invert_yaxis()  # Top model on top
ax.set_xlabel('Mean Absolute Percentage Error - MAPE (%) [Lower is Better]', fontsize=10.5, fontweight='bold')
ax.set_title('7-Day Holdout Validation: Model Accuracy Benchmark Comparison', fontsize=12.5, fontweight='bold', pad=15)

for bar in bars:
    w = bar.get_width()
    ax.text(w + 2, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", va='center', ha='left', fontsize=9, fontweight='bold')

ax.set_xlim(0, max(eval_sorted['MAPE (%)'].iloc[:7]) * 1.25)
fig.tight_layout()
fig.savefig('chart_4_model_benchmark.png', dpi=300)
fig.savefig(os.path.join(ARTIFACT_DIR, 'chart_4_model_benchmark.png'), dpi=300)
plt.close()
print("Saved Chart 4: Model Benchmark")

# CHART 5: 7-Day Future Forecast for Nirlon Knowledge Park
fig, ax = plt.subplots(figsize=(11, 5.5))

# Plot last 21 days of actuals + 7 days forecast
recent_hist = b1_actuals.tail(21).copy()
recent_hist['date_str'] = recent_hist['date'].dt.strftime('%b %d')

f_dates = pd.to_datetime(df_forecast['date'])
f_date_str = f_dates.dt.strftime('%b %d\n(%a)')

# Historical line
all_dates = list(recent_hist['date_str']) + list(f_date_str)
x_hist = np.arange(len(recent_hist))
x_fore = np.arange(len(recent_hist) - 1, len(recent_hist) + len(df_forecast))

ax.plot(x_hist, recent_hist['total_orders'], marker='o', color='#1E293B', linewidth=2, label='Actual Orders (Historical)', zorder=4)

# Forecast line (connecting from last actual)
fore_y = [recent_hist['total_orders'].iloc[-1]] + list(df_forecast['forecast_orders'])
ax.plot(x_fore, fore_y, marker='s', color='#2563EB', linewidth=2.5, linestyle='--', label='7-Day Forecast (Projected)', zorder=4)

# Confidence interval
ci_lower = [recent_hist['total_orders'].iloc[-1]] + list(df_forecast['forecast_orders_lower_95'])
ci_upper = [recent_hist['total_orders'].iloc[-1]] + list(df_forecast['forecast_orders_upper_95'])
ax.fill_between(x_fore, ci_lower, ci_upper, color='#60A5FA', alpha=0.25, label='95% Confidence Interval')

# Forecast data labels
for i, txt in enumerate(df_forecast['forecast_orders']):
    idx = len(recent_hist) + i
    ax.annotate(f"{txt:,}", (idx, txt), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=8.5, fontweight='bold', color='#1E40AF')

ax.axvline(x=len(recent_hist)-1, color='#DC2626', linestyle=':', linewidth=1.5, label='Forecast Origin (2025-04-01)')
ax.set_xticks(range(len(all_dates)))
ax.set_xticklabels(all_dates, rotation=45, ha='right', fontsize=8)
ax.set_ylabel('Daily Order Volume', fontsize=11, fontweight='bold')
ax.set_title('Nirlon Knowledge Park: 7-Day Forward Demand Forecast (Apr 02 - Apr 08, 2025)', fontsize=13, fontweight='bold', pad=15)
ax.legend(loc='upper left', frameon=True)
ax.set_ylim(0, 14000)

fig.tight_layout()
fig.savefig('chart_5_forecast_trajectory.png', dpi=300)
fig.savefig(os.path.join(ARTIFACT_DIR, 'chart_5_forecast_trajectory.png'), dpi=300)
plt.close()
print("Saved Chart 5: Forecast Trajectory")

print("All visual charts generated successfully!")
