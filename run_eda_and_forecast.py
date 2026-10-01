import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

print("=== STARTING COMPREHENSIVE EDA AND FORECASTING PIPELINE ===")

# 1. Load Data
df_daily = pd.read_csv('daily_branch_summary.csv')
df_branches = pd.read_csv('branches.csv')
df_hourly = pd.read_csv('hourly_branch_summary.csv')
df_users = pd.read_csv('users.csv') if os.path.exists('users.csv') else None
df_categories = pd.read_csv('categories.csv') if os.path.exists('categories.csv') else None

print(f"Loaded daily summary: {len(df_daily)} rows")
print(f"Loaded branches: {len(df_branches)} rows")
print(f"Loaded hourly summary: {len(df_hourly)} rows")
if df_users is not None:
    print(f"Loaded users: {len(df_users)} rows")

# 2. Clean and Enhance Daily Data
df_daily['date'] = pd.to_datetime(df_daily['date'])
df_daily = df_daily.sort_values(['branch_id', 'date']).reset_index(drop=True)

# Merge branch metadata
branch_map = df_branches.set_index('id')[['name', 'branch_code', 'branch_manager', 'city_id']].to_dict('index')
df_daily['branch_name'] = df_daily['branch_id'].map(lambda x: branch_map.get(x, {}).get('name', f"Branch {x}"))
df_daily['branch_manager'] = df_daily['branch_id'].map(lambda x: branch_map.get(x, {}).get('branch_manager', 'N/A'))
df_daily['city_name'] = df_daily['branch_id'].map(lambda x: 'Mumbai' if str(branch_map.get(x, {}).get('city_id')) == '1' else ('Bengaluru' if str(branch_map.get(x, {}).get('city_id')) == '2' else 'Hyderabad'))

# Time features
df_daily['day_name'] = df_daily['date'].dt.day_name()
df_daily['day_of_week'] = df_daily['date'].dt.dayofweek # 0=Mon, 6=Sun
df_daily['is_weekend'] = df_daily['day_of_week'].isin([5, 6]).astype(int)
df_daily['month_name'] = df_daily['date'].dt.month_name()
df_daily['year_month'] = df_daily['date'].dt.to_period('M').astype(str)
df_daily['quarter'] = 'Q' + df_daily['date'].dt.quarter.astype(str)

# 3. Overall Portfolio EDA
total_network_orders = df_daily['total_orders'].sum()
total_network_revenue = df_daily['total_revenue'].sum()
total_paid_orders = df_daily['paid_orders'].sum()
total_cancelled_orders = df_daily['cancelled_orders'].sum()
overall_aov = total_network_revenue / total_paid_orders if total_paid_orders > 0 else 0

print("\n--- NETWORK-WIDE EXECUTIVE KPIs ---")
print(f"Total Orders:        {total_network_orders:,}")
print(f"Paid Orders:         {total_paid_orders:,} ({total_paid_orders/total_network_orders*100:.2f}%)")
print(f"Cancelled Orders:    {total_cancelled_orders:,} ({total_cancelled_orders/total_network_orders*100:.2f}%)")
print(f"Gross Network Sales: Rs.{total_network_revenue:,.2f}")
print(f"Average Order Value: Rs.{overall_aov:.2f}")

# Branch ranking table
branch_perf = df_daily.groupby(['branch_id', 'branch_name', 'city_name']).agg(
    total_orders=('total_orders', 'sum'),
    paid_orders=('paid_orders', 'sum'),
    cancelled_orders=('cancelled_orders', 'sum'),
    total_revenue=('total_revenue', 'sum'),
    avg_daily_orders=('total_orders', 'mean'),
    max_daily_orders=('total_orders', 'max'),
    active_days=('date', 'count'),
    first_order_date=('date', 'min'),
    last_order_date=('date', 'max')
).reset_index()

branch_perf['aov'] = (branch_perf['total_revenue'] / branch_perf['paid_orders']).round(2)
branch_perf['order_share_pct'] = (branch_perf['total_orders'] / total_network_orders * 100).round(2)
branch_perf['revenue_share_pct'] = (branch_perf['total_revenue'] / total_network_revenue * 100).round(2)
branch_perf = branch_perf.sort_values('total_orders', ascending=False).reset_index(drop=True)

print("\n--- TOP BRANCHES PERFORMANCE TABLE ---")
print(branch_perf[['branch_id', 'branch_name', 'city_name', 'total_orders', 'total_revenue', 'aov', 'order_share_pct', 'active_days']].to_string(index=False))

# Save Branch Performance Master
branch_perf.to_csv('PowerBI_Branch_Master.csv', index=False)
print("Saved PowerBI_Branch_Master.csv")

# 4. DEEP DIVE ON SELECTED BRANCH: BRANCH 1 (NIRLON KNOWLEDGE PARK)
SELECTED_BRANCH_ID = 1
b1_data = df_daily[df_daily['branch_id'] == SELECTED_BRANCH_ID].copy().sort_values('date').reset_index(drop=True)
print(f"\n=== SELECTED BRANCH FOR MODELING: {b1_data['branch_name'].iloc[0]} (ID: {SELECTED_BRANCH_ID}) ===")
print(f"Observations: {len(b1_data)} continuous days from {b1_data['date'].min().strftime('%Y-%m-%d')} to {b1_data['date'].max().strftime('%Y-%m-%d')}")
print(f"Total Branch Orders: {b1_data['total_orders'].sum():,}")
print(f"Total Branch Revenue: Rs.{b1_data['total_revenue'].sum():,.2f}")
print(f"Mean Daily Orders: {b1_data['total_orders'].mean():.1f} (Std: {b1_data['total_orders'].std():.1f})")

# Feature Engineering for Modeling
b1_data['t'] = np.arange(len(b1_data)) # Time index
b1_data['lag_1'] = b1_data['total_orders'].shift(1)
b1_data['lag_7'] = b1_data['total_orders'].shift(7)
b1_data['lag_14'] = b1_data['total_orders'].shift(14)
b1_data['rolling_mean_7'] = b1_data['total_orders'].shift(1).rolling(7).mean()
b1_data['rolling_mean_14'] = b1_data['total_orders'].shift(1).rolling(14).mean()

# 5. MODEL BENCHMARKING (Train/Test Split)
# Hold out the last 7 days as the Test Validation Set
TEST_HORIZON = 7
train_df = b1_data.iloc[:-TEST_HORIZON].copy().dropna().reset_index(drop=True)
test_df = b1_data.iloc[-TEST_HORIZON:].copy().reset_index(drop=True)

print(f"\n--- TRAIN / TEST SPLIT ---")
print(f"Training Set: {len(train_df)} days ({train_df['date'].min().strftime('%Y-%m-%d')} to {train_df['date'].max().strftime('%Y-%m-%d')})")
print(f"Test Set:     {len(test_df)} days ({test_df['date'].min().strftime('%Y-%m-%d')} to {test_df['date'].max().strftime('%Y-%m-%d')})")
y_test = test_df['total_orders'].values

def evaluate_preds(y_true, y_pred, model_name):
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    return {
        'Model': model_name,
        'MAE': round(mae, 2),
        'RMSE': round(rmse, 2),
        'MAPE (%)': round(mape, 2),
        'R2': round(r2, 4),
        'Predictions': y_pred
    }

models_results = []

# Model 1: Seasonal Naive (Last Week Same Day)
# y_test[i] = y[test_index - 7]
y_pred_snaive = b1_data.iloc[-2*TEST_HORIZON:-TEST_HORIZON]['total_orders'].values
models_results.append(evaluate_preds(y_test, y_pred_snaive, 'Seasonal Naive (Lag-7)'))

# Model 2: 7-Day Moving Average
ma7_val = train_df['total_orders'].tail(7).mean()
y_pred_ma = np.full(TEST_HORIZON, ma7_val)
models_results.append(evaluate_preds(y_test, y_pred_ma, '7-Day Moving Average'))

# Model 3: Day-of-Week Historical Median
dow_medians = train_df.groupby('day_of_week')['total_orders'].median().to_dict()
y_pred_dow_median = test_df['day_of_week'].map(dow_medians).values
models_results.append(evaluate_preds(y_test, y_pred_dow_median, 'Day-of-Week Median Profile'))

# Model 4: Day-of-Week Recent 4-Week Trimmed Mean
# Cafeterias evolve with office occupancy; recent 4 weeks are highly representative
recent_4w = train_df.iloc[-28:]
dow_recent_mean = recent_4w.groupby('day_of_week')['total_orders'].mean().to_dict()
y_pred_recent_dow = test_df['day_of_week'].map(dow_recent_mean).values
models_results.append(evaluate_preds(y_test, y_pred_recent_dow, 'Recent 4-Week DOW Seasonal Mean'))

# Model 5: Ridge / OLS Regression with Linear Trend + Day-of-Week Dummies
# Create feature matrix X
def get_features(df):
    t_feat = df['t'].values[:, None] / 365.0
    # Day of week one-hot (6 dummies, Monday as reference)
    dow_dummies = pd.get_dummies(df['day_of_week'], drop_first=True, prefix='dow').astype(float)
    # Ensure all 6 columns exist
    for col_idx in range(1, 7):
        cname = f'dow_{col_idx}'
        if cname not in dow_dummies.columns:
            dow_dummies[cname] = 0.0
    dow_mat = dow_dummies[[f'dow_{i}' for i in range(1, 7)]].values
    intercept = np.ones((len(df), 1))
    return np.hstack([intercept, t_feat, dow_mat])

X_train = get_features(train_df)
y_train = train_df['total_orders'].values
X_test = get_features(test_df)

# Solve via Ridge (alpha=1.0)
ridge_alpha = 1.0
beta = np.linalg.solve(X_train.T @ X_train + ridge_alpha * np.eye(X_train.shape[1]), X_train.T @ y_train)
y_pred_ridge = X_test @ beta
models_results.append(evaluate_preds(y_test, y_pred_ridge, 'Ridge Regression (Trend + DOW Seasonality)'))

# Model 6: Autoregressive Dynamic Model (Trend + DOW + Lag-7 + Lag-14)
def get_ar_features(df):
    t_feat = df['t'].values[:, None] / 365.0
    dow_dummies = pd.get_dummies(df['day_of_week'], drop_first=True, prefix='dow').astype(float)
    for col_idx in range(1, 7):
        cname = f'dow_{col_idx}'
        if cname not in dow_dummies.columns:
            dow_dummies[cname] = 0.0
    dow_mat = dow_dummies[[f'dow_{i}' for i in range(1, 7)]].values
    lags = df[['lag_7', 'lag_14', 'rolling_mean_7']].values / 10000.0
    intercept = np.ones((len(df), 1))
    return np.hstack([intercept, t_feat, dow_mat, lags])

train_ar = train_df.dropna().copy()
X_train_ar = get_ar_features(train_ar)
y_train_ar = train_ar['total_orders'].values
X_test_ar = get_ar_features(test_df)
beta_ar = np.linalg.solve(X_train_ar.T @ X_train_ar + 2.0 * np.eye(X_train_ar.shape[1]), X_train_ar.T @ y_train_ar)
y_pred_ar = X_test_ar @ beta_ar
models_results.append(evaluate_preds(y_test, y_pred_ar, 'Autoregressive Multi-Seasonal Model'))

# Check if sklearn Random Forest or Gradient Boosting is available
try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    rf = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
    rf.fit(train_ar[['day_of_week', 'is_weekend', 't', 'lag_7', 'lag_14', 'rolling_mean_7']], y_train_ar)
    y_pred_rf = rf.predict(test_df[['day_of_week', 'is_weekend', 't', 'lag_7', 'lag_14', 'rolling_mean_7']])
    models_results.append(evaluate_preds(y_test, y_pred_rf, 'Random Forest Regressor'))
    
    gbr = GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
    gbr.fit(train_ar[['day_of_week', 'is_weekend', 't', 'lag_7', 'lag_14', 'rolling_mean_7']], y_train_ar)
    y_pred_gbr = gbr.predict(test_df[['day_of_week', 'is_weekend', 't', 'lag_7', 'lag_14', 'rolling_mean_7']])
    models_results.append(evaluate_preds(y_test, y_pred_gbr, 'Gradient Boosting Regressor'))
except Exception as e:
    print("Sklearn tree models note:", e)

# Summary Evaluation Table
eval_df = pd.DataFrame([{k: v for k, v in res.items() if k != 'Predictions'} for res in models_results])
eval_df = eval_df.sort_values('MAPE (%)').reset_index(drop=True)
print("\n=== MODEL VALIDATION ACCURACY COMPARISON (7-DAY TEST SET) ===")
print(eval_df.to_string(index=False))

# Export Model Evaluation
eval_df.to_csv('PowerBI_Model_Evaluation.csv', index=False)
print("Saved PowerBI_Model_Evaluation.csv")

# Print Actual vs Predicted on Test Set for the top models
best_model_name = eval_df.iloc[0]['Model']
best_model_res = next(r for r in models_results if r['Model'] == best_model_name)
print(f"\nWinning Model: {best_model_name} (MAPE: {eval_df.iloc[0]['MAPE (%)']}%, RMSE: {eval_df.iloc[0]['RMSE']})")

comparison_test = pd.DataFrame({
    'date': test_df['date'].dt.strftime('%Y-%m-%d'),
    'day_name': test_df['day_name'],
    'actual_orders': y_test,
    'predicted_orders': np.round(best_model_res['Predictions']).astype(int),
    'absolute_error': np.round(np.abs(y_test - best_model_res['Predictions'])).astype(int),
    'percentage_error': np.round(np.abs(y_test - best_model_res['Predictions']) / y_test * 100, 2)
})
print("\n--- TEST SET: ACTUAL VS PREDICTED (DAILY BREAKDOWN) ---")
print(comparison_test.to_string(index=False))

# 6. RETRAIN WINNING MODEL ON FULL DATASET AND GENERATE 7-DAY FUTURE FORECAST
# Forecast Dates: 2025-04-02 (Wed) to 2025-04-08 (Tue)
last_date = b1_data['date'].max()
future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=7, freq='D')

future_df = pd.DataFrame({'date': future_dates})
future_df['branch_id'] = SELECTED_BRANCH_ID
future_df['branch_name'] = b1_data['branch_name'].iloc[0]
future_df['day_name'] = future_df['date'].dt.day_name()
future_df['day_of_week'] = future_df['date'].dt.dayofweek
future_df['is_weekend'] = future_df['day_of_week'].isin([5, 6]).astype(int)
future_df['t'] = np.arange(len(b1_data), len(b1_data) + 7)

# We use the Best Model / Ensemble
# If best is Ridge Regression:
X_full = get_features(b1_data)
y_full = b1_data['total_orders'].values
beta_full = np.linalg.solve(X_full.T @ X_full + ridge_alpha * np.eye(X_full.shape[1]), X_full.T @ y_full)
X_future = get_features(future_df)
y_forecast_ridge = X_future @ beta_full

# Also compute recent 4-week seasonal projection (which captures current office attendance reality):
recent_4w_full = b1_data.iloc[-28:]
dow_full_recent_mean = recent_4w_full.groupby('day_of_week')['total_orders'].mean().to_dict()
y_forecast_recent_dow = future_df['day_of_week'].map(dow_full_recent_mean).values

# Last week same day baseline:
y_forecast_snaive = b1_data.iloc[-7:]['total_orders'].values

# Ensemble / Final Forecast
# Weighted combination: 60% Ridge Regression + 40% Recent 4-Week Seasonal Mean
y_final_forecast = 0.60 * y_forecast_ridge + 0.40 * y_forecast_recent_dow

# Residual standard deviation for 95% Confidence Intervals
residuals = y_full - (X_full @ beta_full)
sigma = np.std(residuals)
lower_ci = np.maximum(0, y_final_forecast - 1.96 * sigma)
upper_ci = y_final_forecast + 1.96 * sigma

# Calculate Estimated Revenue based on Branch 1 recent AOV
recent_aov = b1_data.iloc[-30:]['avg_order_value'].mean()
forecast_revenue = y_final_forecast * recent_aov

future_df['forecast_orders'] = np.round(y_final_forecast).astype(int)
future_df['forecast_orders_lower_95'] = np.round(lower_ci).astype(int)
future_df['forecast_orders_upper_95'] = np.round(upper_ci).astype(int)
future_df['estimated_aov'] = round(recent_aov, 2)
future_df['estimated_revenue'] = np.round(forecast_revenue, 2)

print("\n=============================================================")
print("=== OFFICIAL 7-DAY FORECAST FOR NIRLON KNOWLEDGE PARK ===")
print("=============================================================")
print(future_df[['date', 'day_name', 'forecast_orders', 'forecast_orders_lower_95', 'forecast_orders_upper_95', 'estimated_revenue']].to_string(index=False))

total_forecasted_orders = future_df['forecast_orders'].sum()
total_forecasted_rev = future_df['estimated_revenue'].sum()
print(f"\nProjected Total 7-Day Orders:  {total_forecasted_orders:,} orders")
print(f"Projected Total 7-Day Revenue: Rs.{total_forecasted_rev:,.2f}")
print(f"Average Daily Volume:          {total_forecasted_orders/7:,.0f} orders/day")

# 7. EXPORT COMBINED POWERBI DATASETS
# Create a unified Time Series dataset for Power BI (Actuals + Forecast)
history_export = b1_data[['date', 'branch_id', 'branch_name', 'day_name', 'is_weekend', 'total_orders', 'paid_orders', 'cancelled_orders', 'total_revenue', 'avg_order_value', 'pos_orders', 'app_orders', 'sok_orders', 'unique_customers']].copy()
history_export['data_type'] = 'Actual'
history_export['forecast_orders'] = history_export['total_orders']
history_export['lower_bound_95'] = history_export['total_orders']
history_export['upper_bound_95'] = history_export['total_orders']

future_export = pd.DataFrame({
    'date': future_df['date'],
    'branch_id': SELECTED_BRANCH_ID,
    'branch_name': b1_data['branch_name'].iloc[0],
    'day_name': future_df['day_name'],
    'is_weekend': future_df['is_weekend'],
    'total_orders': future_df['forecast_orders'],
    'paid_orders': future_df['forecast_orders'],
    'cancelled_orders': 0,
    'total_revenue': future_df['estimated_revenue'],
    'avg_order_value': future_df['estimated_aov'],
    'pos_orders': np.round(future_df['forecast_orders'] * 0.70).astype(int), # Historical ~70% POS
    'app_orders': np.round(future_df['forecast_orders'] * 0.20).astype(int), # Historical ~20% App
    'sok_orders': np.round(future_df['forecast_orders'] * 0.10).astype(int), # Historical ~10% Kiosk
    'unique_customers': np.round(future_df['forecast_orders'] * 0.85).astype(int),
    'data_type': 'Forecast',
    'forecast_orders': future_df['forecast_orders'],
    'lower_bound_95': future_df['forecast_orders_lower_95'],
    'upper_bound_95': future_df['forecast_orders_upper_95']
})

combined_b1 = pd.concat([history_export, future_export], ignore_index=True)
combined_b1.to_csv('PowerBI_Branch1_Daily_Forecast.csv', index=False)
print("\nSaved PowerBI_Branch1_Daily_Forecast.csv (Historical + Forecast combined)")

# Save standalone forecast file
future_df.to_csv('PowerBI_7Day_Forecast_Results.csv', index=False)
print("Saved PowerBI_7Day_Forecast_Results.csv")

# 8. Export Hourly Breakdown with Branch and City
df_hourly['branch_name'] = df_hourly['branch_id'].map(lambda x: branch_map.get(x, {}).get('name', f"Branch {x}"))
df_hourly['time_of_day'] = df_hourly['hour'].map(lambda h: 'Breakfast (7-11)' if 7 <= h < 11 else ('Lunch Peak (11-15)' if 11 <= h < 15 else ('Snacks / Evening (15-19)' if 15 <= h < 19 else 'Night / Off-Peak')))
df_hourly.to_csv('PowerBI_Hourly_Distribution.csv', index=False)
print("Saved PowerBI_Hourly_Distribution.csv")

# 9. Channel and Payment Aggregates for All Branches
channel_payment_rows = []
for b_id, g in df_daily.groupby('branch_id'):
    bname = branch_map.get(b_id, {}).get('name', f"Branch {b_id}")
    channel_payment_rows.append({
        'branch_id': b_id,
        'branch_name': bname,
        'pos_orders': g['pos_orders'].sum(),
        'app_orders': g['app_orders'].sum(),
        'sok_orders': g['sok_orders'].sum(),
        'cash_orders': g['cash_orders'].sum(),
        'qr_orders': g['qr_orders'].sum(),
        'upi_orders': g['upi_orders'].sum(),
        'card_orders': g['card_orders'].sum(),
        'wallet_orders': g['wallet_orders'].sum(),
        'total_orders': g['total_orders'].sum(),
        'total_revenue': g['total_revenue'].sum()
    })
df_cp = pd.DataFrame(channel_payment_rows)
df_cp.to_csv('PowerBI_Channel_Payment_Mix.csv', index=False)
print("Saved PowerBI_Channel_Payment_Mix.csv")

# 10. Master Daily Summary with names for Power BI
df_daily.to_csv('PowerBI_Daily_Branch_Summary.csv', index=False)
print("Saved PowerBI_Daily_Branch_Summary.csv")

print("\n=== PIPELINE EXECUTION COMPLETED SUCCESSFULLY! ===")
