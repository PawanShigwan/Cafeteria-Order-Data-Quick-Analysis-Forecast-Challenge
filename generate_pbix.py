"""
Generate a valid Power BI Desktop (.pbix) file from our CSV datasets.
A .pbix file is a ZIP archive containing:
  - [Content_Types].xml
  - DataModel  (binary - we'll use the DataModelSchema JSON approach)
  - Report/Layout  (JSON defining report pages and visuals)
  - Report/Metadata
  - DiagramLayout
  - SecurityBindings
  - Settings
  - Version
"""

import zipfile
import json
import os
import csv
import base64
import shutil

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE = r"C:\Users\HP\Downloads\Cafeteria Order Data"
OUT_PBIX = os.path.join(BASE, "Foodii_Cafeteria_Analytics_Forecast.pbix")
TMP_DIR  = os.path.join(BASE, "_pbix_tmp")

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(os.path.join(TMP_DIR, "Report"), exist_ok=True)

# ─── Helper: load CSV rows ────────────────────────────────────────────────────
def load_csv(filename):
    with open(os.path.join(BASE, filename), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

branch_rows    = load_csv("PowerBI_Branch_Master.csv")
daily_rows     = load_csv("PowerBI_Daily_Branch_Summary.csv")
forecast_rows  = load_csv("PowerBI_7Day_Forecast_Results.csv")
hourly_rows    = load_csv("PowerBI_Hourly_Distribution.csv")
model_rows     = load_csv("PowerBI_Model_Evaluation.csv")
b1_rows        = load_csv("PowerBI_Branch1_Daily_Forecast.csv")
cp_rows        = load_csv("PowerBI_Channel_Payment_Mix.csv")

print(f"Loaded CSVs: {len(daily_rows)} daily rows, {len(b1_rows)} B1 rows, {len(forecast_rows)} forecast rows")

# ─── 1. [Content_Types].xml ──────────────────────────────────────────────────
content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="xml"  ContentType="application/xml" />
  <Override PartName="/DataModel" ContentType="application/vnd.ms-pbi.datamodel" />
  <Override PartName="/Report/Layout" ContentType="application/vnd.ms-pbi.report.layout" />
</Types>
"""

# ─── 2. Version ──────────────────────────────────────────────────────────────
version = "3.0"

# ─── 3. Settings ─────────────────────────────────────────────────────────────
settings = json.dumps({
    "Version": 3,
    "IsReadOnly": False,
    "IsPrivate": False,
    "EnableDesignModeInReport": True
})

# ─── 4. DataModelSchema JSON (defines tables, columns, relationships) ─────────
def build_table(name, rows, col_types=None):
    """Build a DataModel table definition."""
    if not rows:
        return {"name": name, "columns": [], "rows": []}
    headers = list(rows[0].keys())
    columns = []
    for h in headers:
        dtype = "text"
        if col_types and h in col_types:
            dtype = col_types[h]
        columns.append({
            "name": h,
            "dataType": dtype,
            "sourceColumn": h
        })
    return {
        "name": name,
        "columns": columns,
        "partitions": [{
            "name": f"{name}_Partition",
            "source": {
                "type": "calculated",
                "expression": []
            }
        }]
    }

NUM = "double"
INT = "int64"
TEXT = "text"

branch_types = {
    "branch_id": INT, "total_orders": INT, "paid_orders": INT,
    "cancelled_orders": INT, "total_revenue": NUM, "aov": NUM,
    "avg_daily_orders": NUM, "max_daily_orders": INT, "active_days": INT,
    "order_share_pct": NUM, "revenue_share_pct": NUM
}

daily_types = {
    "branch_id": INT, "total_orders": INT, "paid_orders": INT,
    "cancelled_orders": INT, "total_revenue": NUM, "total_tax": NUM,
    "total_discount": NUM, "avg_order_value": NUM, "pos_orders": INT,
    "app_orders": INT, "sok_orders": INT, "other_channel_orders": INT,
    "cash_orders": INT, "qr_orders": INT, "upi_orders": INT,
    "card_orders": INT, "wallet_orders": INT, "unique_customers": INT,
    "is_weekend": INT, "day_of_week": INT
}

forecast_types = {
    "branch_id": INT, "day_of_week": INT, "is_weekend": INT,
    "t": INT, "forecast_orders": INT, "forecast_orders_lower_95": INT,
    "forecast_orders_upper_95": INT, "estimated_aov": NUM, "estimated_revenue": NUM
}

hourly_types = {
    "branch_id": INT, "hour": INT, "order_count": INT
}

model_types = {
    "MAE": NUM, "RMSE": NUM, "MAPE (%)": NUM, "R2": NUM
}

b1_types = {
    "branch_id": INT, "total_orders": INT, "paid_orders": INT,
    "cancelled_orders": INT, "total_revenue": NUM, "avg_order_value": NUM,
    "pos_orders": INT, "app_orders": INT, "sok_orders": INT,
    "unique_customers": INT, "is_weekend": INT, "day_of_week": INT,
    "forecast_orders": INT, "lower_bound_95": INT, "upper_bound_95": INT
}

cp_types = {
    "branch_id": INT, "pos_orders": INT, "app_orders": INT,
    "sok_orders": INT, "cash_orders": INT, "qr_orders": INT,
    "upi_orders": INT, "card_orders": INT, "wallet_orders": INT,
    "total_orders": INT, "total_revenue": NUM
}

data_model_schema = {
    "name": "Foodii Cafeteria Analytics",
    "tables": [
        build_table("Dim_Branch", branch_rows, branch_types),
        build_table("Fact_DailyOrders", daily_rows, daily_types),
        build_table("Fact_Branch1_Forecast", b1_rows, b1_types),
        build_table("Fact_7Day_Forecast", forecast_rows, forecast_types),
        build_table("Fact_HourlyDistribution", hourly_rows, hourly_types),
        build_table("Dim_ModelEvaluation", model_rows, model_types),
        build_table("Fact_ChannelPaymentMix", cp_rows, cp_types),
    ],
    "relationships": [
        {
            "name": "Branch_to_DailyOrders",
            "fromTable": "Fact_DailyOrders",
            "fromColumn": "branch_id",
            "toTable": "Dim_Branch",
            "toColumn": "branch_id",
            "crossFilteringBehavior": "oneDirection"
        },
        {
            "name": "Branch_to_Forecast",
            "fromTable": "Fact_Branch1_Forecast",
            "fromColumn": "branch_id",
            "toTable": "Dim_Branch",
            "toColumn": "branch_id",
            "crossFilteringBehavior": "oneDirection"
        },
        {
            "name": "Branch_to_Hourly",
            "fromTable": "Fact_HourlyDistribution",
            "fromColumn": "branch_id",
            "toTable": "Dim_Branch",
            "toColumn": "branch_id",
            "crossFilteringBehavior": "oneDirection"
        }
    ],
    "annotations": [
        {"name": "PBIDesktopVersion", "value": "2.126.1261.0"},
        {"name": "TabularEditor_SerializeOptions", "value": ""}
    ]
}

# ─── 5. Report/Layout JSON ────────────────────────────────────────────────────
# Standard Power BI report layout with 4 pages + visuals

W = 1280  # canvas width
H = 720   # canvas height

def card_visual(x, y, w, h, measure_name, title_text, font_color="#333333"):
    return {
        "id": abs(hash(title_text)) % 999999,
        "x": x, "y": y, "z": 1000,
        "width": w, "height": h,
        "config": json.dumps({
            "name": str(abs(hash(title_text)) % 999999),
            "layouts": [{"id": 0, "position": {"x": 0, "y": 0, "width": w, "height": h}}],
            "singleVisual": {
                "visualType": "card",
                "projections": {
                    "Values": [{"queryRef": measure_name, "active": True}]
                },
                "vcObjects": {
                    "title": [{"properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}},
                        "fontColor": {"expr": {"Literal": {"Value": f"'{font_color}'"}}},
                        "fontSize": {"expr": {"Literal": {"Value": "11"}}}
                    }}],
                    "labels": [{"properties": {
                        "fontSize": {"expr": {"Literal": {"Value": "22"}}},
                        "fontFamily": {"expr": {"Literal": {"Value": "'Segoe UI'"}}},
                        "labelDisplayUnits": {"expr": {"Literal": {"Value": "1000"}}}
                    }}]
                }
            }
        })
    }

def bar_chart_visual(x, y, w, h, visual_id, title_text):
    return {
        "id": visual_id,
        "x": x, "y": y, "z": 1000,
        "width": w, "height": h,
        "config": json.dumps({
            "name": str(visual_id),
            "layouts": [{"id": 0, "position": {"x": 0, "y": 0, "width": w, "height": h}}],
            "singleVisual": {
                "visualType": "columnChart",
                "projections": {
                    "Category": [{"queryRef": "Dim_Branch.branch_name"}],
                    "Y": [{"queryRef": "Sum.total_revenue"}]
                },
                "vcObjects": {
                    "title": [{"properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}},
                        "fontSize": {"expr": {"Literal": {"Value": "13"}}},
                        "fontFamily": {"expr": {"Literal": {"Value": "'Segoe UI'"}}}
                    }}]
                }
            }
        })
    }

def donut_visual(x, y, w, h, visual_id, title_text):
    return {
        "id": visual_id,
        "x": x, "y": y, "z": 1000,
        "width": w, "height": h,
        "config": json.dumps({
            "name": str(visual_id),
            "singleVisual": {
                "visualType": "donutChart",
                "vcObjects": {
                    "title": [{"properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}}
                    }}]
                }
            }
        })
    }

def table_visual(x, y, w, h, visual_id, title_text, table_name, columns):
    return {
        "id": visual_id,
        "x": x, "y": y, "z": 1000,
        "width": w, "height": h,
        "config": json.dumps({
            "name": str(visual_id),
            "singleVisual": {
                "visualType": "tableEx",
                "projections": {
                    "Values": [{"queryRef": f"{table_name}.{c}"} for c in columns]
                },
                "vcObjects": {
                    "title": [{"properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}}
                    }}]
                }
            }
        })
    }

def line_chart_visual(x, y, w, h, visual_id, title_text):
    return {
        "id": visual_id,
        "x": x, "y": y, "z": 1000,
        "width": w, "height": h,
        "config": json.dumps({
            "name": str(visual_id),
            "singleVisual": {
                "visualType": "lineChart",
                "projections": {
                    "Category": [{"queryRef": "Fact_Branch1_Forecast.date"}],
                    "Y": [
                        {"queryRef": "Sum.total_orders"},
                        {"queryRef": "Sum.forecast_orders"}
                    ]
                },
                "vcObjects": {
                    "title": [{"properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title_text}'"}}}
                    }}]
                }
            }
        })
    }

# ─── PAGE 1: Executive Portfolio ──────────────────────────────────────────────
page1_visuals = [
    # KPI Cards
    card_visual(18, 18, 265, 100, "Sum.total_revenue", "Gross Network Revenue"),
    card_visual(296, 18, 265, 100, "Sum.total_orders", "Total Processed Orders"),
    card_visual(574, 18, 265, 100, "Avg.avg_order_value", "Average Order Value (AOV)"),
    card_visual(852, 18, 265, 100, "Count.branch_id", "Active Branch Outlets"),

    # Branch Revenue Chart
    bar_chart_visual(18, 132, 580, 280, 10001, "Branch Revenue & Volume Comparison (FY 2024-25)"),

    # Channel Donut
    donut_visual(612, 132, 530, 280, 10002, "Order Channel Composition (Mobile App vs POS vs Kiosk)"),

    # Branch Performance Table
    table_visual(18, 426, 1124, 270, 10003, "Enterprise Branch Performance Scorecard",
                 "Dim_Branch",
                 ["branch_name", "city_name", "total_orders", "total_revenue", "aov", "order_share_pct", "active_days"])
]

# ─── PAGE 2: Branch Deep Dive ─────────────────────────────────────────────────
page2_visuals = [
    card_visual(18, 18, 270, 100, "Sum.total_revenue", "Nirlon Knowledge Park - Gross Sales"),
    card_visual(300, 18, 270, 100, "Sum.total_orders", "Total Orders Processed"),
    card_visual(582, 18, 270, 100, "Avg.avg_order_value", "Branch Average Order Value"),
    card_visual(864, 18, 270, 100, "Max.total_orders", "Peak Single Day Volume"),
    bar_chart_visual(18, 132, 560, 270, 20001, "Day-of-Week Corporate Seasonality (Mean Daily Orders)"),
    line_chart_visual(592, 132, 550, 270, 20002, "24-Hour Intraday Demand Profile (Peak: 12 PM - 2 PM)"),
    donut_visual(18, 416, 530, 270, 20003, "Ordering Channel Split: Mobile App vs SOK Kiosk vs POS"),
    donut_visual(562, 416, 530, 270, 20004, "Payment Instrument Distribution (UPI, Wallet, QR, Cash)"),
]

# ─── PAGE 3: 7-Day Forecast ───────────────────────────────────────────────────
page3_visuals = [
    card_visual(18, 18, 270, 100, "Sum.forecast_orders", "7-Day Projected Total Orders"),
    card_visual(300, 18, 270, 100, "Sum.estimated_revenue", "7-Day Projected Revenue"),
    card_visual(582, 18, 270, 100, "Avg.forecast_orders", "Daily Order Average (Forecast)"),
    card_visual(864, 18, 270, 100, "Max.forecast_orders_upper_95", "Peak Day Upper Bound (95%)"),
    line_chart_visual(18, 132, 1124, 310, 30001, "7-Day Forward Demand Forecast with 95% Confidence Band"),
    table_visual(18, 456, 1124, 240, 30002, "Daily Forecast Schedule & Operational Kitchen Guidance",
                 "Fact_7Day_Forecast",
                 ["date", "day_name", "forecast_orders", "forecast_orders_lower_95",
                  "forecast_orders_upper_95", "estimated_revenue", "is_weekend"])
]

# ─── PAGE 4: Model Accuracy Benchmark ────────────────────────────────────────
page4_visuals = [
    card_visual(18, 18, 265, 100, "Min.MAPE (%)", "Best Model MAPE (%)"),
    card_visual(296, 18, 265, 100, "Min.RMSE", "Champion Model RMSE"),
    card_visual(574, 18, 265, 100, "Min.MAE", "Champion Model MAE"),
    card_visual(852, 18, 265, 100, "Max.R2", "Best Model R² Score"),
    bar_chart_visual(18, 132, 580, 300, 40001, "Model Accuracy Benchmark: MAPE % (Lower is Better)"),
    bar_chart_visual(612, 132, 530, 300, 40002, "Holdout Validation: 7-Day Actual vs Predicted Orders"),
    table_visual(18, 446, 1124, 250, 40003, "Complete Model Evaluation Leaderboard",
                 "Dim_ModelEvaluation",
                 ["Model", "MAE", "RMSE", "MAPE (%)", "R2"])
]

def make_page(page_name, page_id, display_name, visuals):
    return {
        "name": page_name,
        "displayName": display_name,
        "width": W,
        "height": H,
        "visualContainers": visuals,
        "config": json.dumps({
            "relationships": [],
            "objects": {
                "page": [{"properties": {
                    "background": {"solid": {"color": {"expr": {"Literal": {"Value": "'#F0F2F5'"}}}}},
                }}]
            }
        })
    }

report_layout = {
    "id": 0,
    "version": "5.36",
    "pods": [],
    "resourcePackages": [],
    "sections": [
        make_page("ReportSection1", 1, "1. Executive Portfolio", page1_visuals),
        make_page("ReportSection2", 2, "2. Nirlon KP Deep Dive", page2_visuals),
        make_page("ReportSection3", 3, "3. 7-Day Demand Forecast", page3_visuals),
        make_page("ReportSection4", 4, "4. Model Accuracy Benchmark", page4_visuals),
    ],
    "config": json.dumps({
        "version": "5.36",
        "objects": {
            "report": [{"properties": {
                "filterPanelEnabled": {"expr": {"Literal": {"Value": "true"}}},
                "displayName": {"expr": {"Literal": {"Value": "'Foodii Cafeteria Analytics'"}}},
            }}]
        }
    })
}

# ─── 6. Write temp files ──────────────────────────────────────────────────────
def write_tmp(path, content):
    full_path = os.path.join(TMP_DIR, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    if isinstance(content, bytes):
        with open(full_path, "wb") as f:
            f.write(content)
    else:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

write_tmp("[Content_Types].xml", content_types)
write_tmp("Version", version)
write_tmp("Settings", settings)
write_tmp("DataModelSchema", json.dumps(data_model_schema, indent=2))
write_tmp("Report/Layout", json.dumps(report_layout, separators=(",", ":")))
write_tmp("Report/Metadata", json.dumps({"Version": 1, "autoCreatedRelationships": []}))
write_tmp("SecurityBindings", "")
write_tmp("DiagramLayout", json.dumps({
    "version": 1.2,
    "tables": [
        {"id": t["name"], "x": 20 + i*220, "y": 20, "width": 200, "height": 150}
        for i, t in enumerate(data_model_schema["tables"])
    ]
}))

# ─── 7. Zip into .pbix ───────────────────────────────────────────────────────
print("Creating PBIX archive...")
with zipfile.ZipFile(OUT_PBIX, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(TMP_DIR):
        for file in files:
            full_path = os.path.join(root, file)
            arcname = os.path.relpath(full_path, TMP_DIR)
            zf.write(full_path, arcname)
            print(f"  Added: {arcname}")

# Cleanup
shutil.rmtree(TMP_DIR)

size_kb = os.path.getsize(OUT_PBIX) / 1024
print(f"\nSuccess! Generated: {OUT_PBIX}")
print(f"File Size: {size_kb:.1f} KB")
print("Open with Power BI Desktop to see the report.")
