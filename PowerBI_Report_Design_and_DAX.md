# Power BI Report Architecture & DAX Modeling Guide
## Foodii Cafeteria Order Intelligence & 7-Day Demand Forecasting

This guide provides end-to-end specifications to build the enterprise Power BI report using the clean exported datasets generated from the 11 GB Cafeteria Order Database.

---

## 1. Data Model Architecture (Star Schema)

The model is designed around clean dimensional modeling principles to ensure sub-second query performance and intuitive DAX calculations.

```
                    ┌─────────────────────────┐
                    │      Dim_Calendar       │
                    │   (Date Dimension)      │
                    └────────────┬────────────┘
                                 │ 1
                                 │
                                 │ *
┌───────────────────────┐   ┌────┴────────────────────────┐   ┌────────────────────────┐
│     Dim_Branch        │   │        Fact_DailyOrders     │   │      Dim_Channel       │
│  (Branches Master)    ├───┤  (All Branches 2024-2025)   ├───┤   (POS, App, Kiosk)    │
└───────────────────────┘ 1 │ *                           │ 1 └────────────────────────┘
                            └─────────────────────────────┘
                                         │
                                         │ 1
                                         │
                                         │ *
                            ┌────────────┴────────────────┐
                            │    Fact_Branch1_Forecast    │
                            │ (History + 7-Day Forecast)  │
                            └─────────────────────────────┘
```

### Table Mappings & Source Files

| Table Name in Power BI | Source File | Type | Description |
| :--- | :--- | :--- | :--- |
| **`Fact_DailyOrders`** | `PowerBI_Daily_Branch_Summary.csv` | Fact | Daily aggregated orders, sales, tax, discount, channels, and payment counts for all 18 branches (1,415 rows). |
| **`Fact_Branch1_Forecast`** | `PowerBI_Branch1_Daily_Forecast.csv` | Fact | Continuous time series for Nirlon Knowledge Park (366 historical days + 7 forecast days with lower/upper 95% CI). |
| **`Dim_Branch`** | `PowerBI_Branch_Master.csv` | Dimension | Branch metadata: branch_id, branch_name, city_name, branch_code, manager, total historical volume, AOV. |
| **`Fact_HourlyDistribution`** | `PowerBI_Hourly_Distribution.csv` | Fact/Bridge | Hourly demand distribution (hours 0–23) across branches for intraday staffing analysis. |
| **`Dim_ModelEvaluation`** | `PowerBI_Model_Evaluation.csv` | Dimension | Benchmark metrics (MAE, RMSE, MAPE, R²) for the 8 tested forecasting algorithms. |

### Relationships Configuration
1. `Dim_Branch[branch_id]` (1) ───< `Fact_DailyOrders[branch_id]` (*) [Single direction]
2. `Dim_Branch[branch_id]` (1) ───< `Fact_Branch1_Forecast[branch_id]` (*) [Single direction]
3. `Dim_Calendar[Date]` (1) ───< `Fact_DailyOrders[date]` (*) [Single direction]
4. `Dim_Calendar[Date]` (1) ───< `Fact_Branch1_Forecast[date]` (*) [Single direction]

---

## 2. Core DAX Measures (Ready to Copy-Paste)

Create a dedicated table named `_Measures` in Power BI and add the following DAX calculations:

### Section A: Enterprise Portfolio Measures

```dax
// 1. Total Order Volume
Total Orders = 
SUM(Fact_DailyOrders[total_orders])

// 2. Total Paid Orders
Total Paid Orders = 
SUM(Fact_DailyOrders[paid_orders])

// 3. Gross Network Revenue (INR)
Gross Revenue = 
SUM(Fact_DailyOrders[total_revenue])

// 4. Gross Revenue in Crores (for Executive Cards)
Gross Revenue (Cr) = 
DIVIDE([Gross Revenue], 10000000, 0)

// 5. Average Order Value (AOV)
AOV = 
DIVIDE([Gross Revenue], [Total Paid Orders], 0)

// 6. Total Cancelled Orders
Cancelled Orders = 
SUM(Fact_DailyOrders[cancelled_orders])

// 7. Cancellation Rate %
Cancellation Rate % = 
DIVIDE([Cancelled Orders], [Total Orders], 0)

// 8. Mobile App Order Share %
App Order Share % = 
DIVIDE(SUM(Fact_DailyOrders[app_orders]), [Total Orders], 0)

// 9. Self-Ordering Kiosk (SOK) Share %
Kiosk Order Share % = 
DIVIDE(SUM(Fact_DailyOrders[sok_orders]), [Total Orders], 0)

// 10. Traditional POS Share %
POS Order Share % = 
DIVIDE(SUM(Fact_DailyOrders[pos_orders]), [Total Orders], 0)

// 11. Digital Payment Adoption Rate %
Digital Payment Share % = 
DIVIDE(
    SUM(Fact_DailyOrders[upi_orders]) + SUM(Fact_DailyOrders[wallet_orders]) + SUM(Fact_DailyOrders[qr_orders]) + SUM(Fact_DailyOrders[card_orders]),
    [Total Orders],
    0
)
```

### Section B: Branch 1 Forecasting & Time Series Measures

```dax
// 12. Actual Orders (Historical Only)
Actual Orders = 
CALCULATE(
    SUM(Fact_Branch1_Forecast[total_orders]),
    Fact_Branch1_Forecast[data_type] = "Actual"
)

// 13. Forecasted Orders (Next 7 Days Only)
Forecasted Orders = 
CALCULATE(
    SUM(Fact_Branch1_Forecast[forecast_orders]),
    Fact_Branch1_Forecast[data_type] = "Forecast"
)

// 14. Combined Actual & Forecast Line
Actual and Forecast Orders = 
COALESCE([Actual Orders], [Forecasted Orders])

// 15. 95% Confidence Interval Upper Bound
Forecast Upper Bound (95%) = 
CALCULATE(
    MAX(Fact_Branch1_Forecast[upper_bound_95]),
    Fact_Branch1_Forecast[data_type] = "Forecast"
)

// 16. 95% Confidence Interval Lower Bound
Forecast Lower Bound (95%) = 
CALCULATE(
    MIN(Fact_Branch1_Forecast[lower_bound_95]),
    Fact_Branch1_Forecast[data_type] = "Forecast"
)

// 17. 7-Day Projected Total Orders
7-Day Projected Total Orders = 
CALCULATE(
    SUM(Fact_Branch1_Forecast[forecast_orders]),
    Fact_Branch1_Forecast[data_type] = "Forecast"
)

// 18. 7-Day Projected Total Revenue
7-Day Projected Revenue = 
CALCULATE(
    SUM(Fact_Branch1_Forecast[total_revenue]),
    Fact_Branch1_Forecast[data_type] = "Forecast"
)

// 19. 7-Day Projected Daily Run Rate
7-Day Avg Daily Forecast = 
DIVIDE([7-Day Projected Total Orders], 7, 0)

// 20. Peak Lunch Hour Concentration %
Peak Lunch Concentration % = 
VAR LunchOrders = 
    CALCULATE(
        SUM(Fact_HourlyDistribution[order_count]),
        Fact_HourlyDistribution[hour] IN {11, 12, 13, 14},
        Fact_HourlyDistribution[branch_id] = 1
    )
VAR TotalBranchOrders = 
    CALCULATE(
        SUM(Fact_HourlyDistribution[order_count]),
        Fact_HourlyDistribution[branch_id] = 1
    )
RETURN
DIVIDE(LunchOrders, TotalBranchOrders, 0)
```

---

## 3. Power BI Report Page Layout & Visual Specifications

### Page 1: Executive Portfolio Overview
- **Visual 1 (Top Cards Row)**:
  - Card 1: `[Gross Revenue (Cr)]` with callout subtitle `₹41.10 Crores Gross Sales`
  - Card 2: `[Total Orders]` with callout subtitle `5,961,005 Completed Orders`
  - Card 3: `[AOV]` with callout `₹68.96 Average Ticket`
  - Card 4: `[Digital Payment Share %]` with callout `99.04% Cashless Ratio`
- **Visual 2 (Clustered Column & Line Chart)**:
  - X-Axis: `Dim_Branch[branch_name]`
  - Column Y-Axis: `[Gross Revenue]`
  - Line Y-Axis: `[Total Orders]`
  - Title: *"Gross Revenue & Order Volume by Operating Branch"*
- **Visual 3 (Donut Chart)**:
  - Legend: Channel Name (Mobile App, SOK Kiosk, POS Counter)
  - Values: `[Total Orders]`
  - Title: *"Enterprise Channel Share: Digital App Dominance"*
- **Visual 4 (Leaderboard Table)**:
  - Columns: `Rank`, `branch_name`, `city_name`, `[Total Orders]`, `[Gross Revenue]`, `[AOV]`, `[Cancellation Rate %]`

### Page 2: Branch Deep Dive – Nirlon Knowledge Park (Branch 1)
- **Visual 1 (Top Cards Row)**:
  - Card 1: `[Gross Revenue]` filtered to Branch 1 (`₹17.02 Crores`)
  - Card 2: `[Total Orders]` filtered to Branch 1 (`2,344,842 Orders`)
  - Card 3: `[AOV]` filtered to Branch 1 (`₹72.60`)
  - Card 4: `[Peak Lunch Concentration %]` (`42.8% of daily demand between 11 AM - 2 PM`)
- **Visual 2 (Column Chart - Day of Week Seasonality)**:
  - X-Axis: `Day Name` (Sorted by `day_of_week`: Mon -> Sun)
  - Y-Axis: `Average Daily Orders`
  - Data Labels: On
  - Highlighting: Tue/Wed/Thu peak at ~9,100+ orders; Sat/Sun drops to ~400–1,000 orders.
- **Visual 3 (Area Chart - 24-Hour Intraday Demand Curve)**:
  - X-Axis: `Fact_HourlyDistribution[hour]` (0 to 23)
  - Y-Axis: `SUM(Fact_HourlyDistribution[order_count])`
  - Annotations: Dual-peak profile (12:00–14:00 Lunch Rush; 16:00–18:00 Snack/Beverage Surge)
- **Visual 4 (Stacked Bar Chart - Payment Instruments)**:
  - Y-Axis: Payment Type (Prepaid Wallet, UPI, Dynamic QR, Card, Cash)
  - X-Axis: Volume share %

### Page 3: 7-Day Demand Forecasting & Operations
- **Visual 1 (Top Cards Row)**:
  - Card 1: `[7-Day Projected Total Orders]` (`44,961 Orders`)
  - Card 2: `[7-Day Projected Revenue]` (`₹31.46 Lakhs`)
  - Card 3: `[7-Day Avg Daily Forecast]` (`6,423 Orders/Day`)
  - Card 4: `Forecast Period: Apr 02 - Apr 08, 2025`
- **Visual 2 (Line Chart with Shaded Prediction Band)**:
  - X-Axis: `Fact_Branch1_Forecast[date]`
  - Series 1: `[Actual Orders]` (Solid Dark Navy `#1E293B`)
  - Series 2: `[Forecasted Orders]` (Dashed Vibrant Blue `#2563EB`)
  - Series 3: `[Forecast Upper Bound (95%)]` (Light Blue fill)
  - Series 4: `[Forecast Lower Bound (95%)]`
  - Visual Cue: Vertical line at `2025-04-01` indicating Forecast Origin.
- **Visual 3 (Operational Kitchen & Staffing Schedule Grid)**:
  - Table visual mapping each day (Apr 02 to Apr 08) to:
    - Expected Orders
    - Staffing Allocation (Full, Hybrid, Weekend Skeleton)
    - Kitchen Meal Prep Targets

### Page 4: Model Benchmarking & Accuracy Validation
- **Visual 1 (Horizontal Bar Chart)**:
  - Y-Axis: `Dim_ModelEvaluation[Model]`
  - X-Axis: `Dim_ModelEvaluation[MAPE (%)]` (Sorted Ascending - Champion on top)
  - Data Labels: 45.3%, 47.0%, 47.8%, 50.2%, 54.6%, etc.
- **Visual 2 (Clustered Column Chart - Holdout Validation)**:
  - X-Axis: 7 Test Holdout Dates (Mar 26 to Apr 01)
  - Series 1: `Actual Orders`
  - Series 2: `Predicted Orders`
- **Visual 3 (Full Metrics Matrix)**:
  - Columns: `Model`, `MAE`, `RMSE`, `MAPE (%)`, `R² Score`, `Status`

---

## 4. How to Load and Refresh in Power BI Desktop

1. Open **Power BI Desktop**.
2. Click **Get Data** -> **Text/CSV**.
3. Select `PowerBI_Daily_Branch_Summary.csv`, `PowerBI_Branch_Master.csv`, `PowerBI_Branch1_Daily_Forecast.csv`, `PowerBI_Hourly_Distribution.csv`, and `PowerBI_Model_Evaluation.csv`.
4. In **Model View**, verify the star schema relationships listed in Section 1.
5. Create a new table `_Measures` and copy-paste the DAX formulas from Section 2.
6. Build the visual canvases according to the layout grids above.
7. Save as `Foodii_Cafeteria_Analytics_and_Forecast.pbix`.
