"""
app.py — Avocado Sales Dashboard (v2)
Single-page tabbed layout · Deep Navy & Gold palette
Run: python app.py  →  http://127.0.0.1:8050
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pathlib import Path

# ── DATA LOADING (all pandas logic unchanged) ─────────────────────────────────
CSV_PATH = Path(__file__).parent / "avocado.csv"

def load_data():
    avocado = pd.read_csv(CSV_PATH)
    avocado.columns = (avocado.columns.str.strip().str.lower()
                       .str.replace(" ", "_").str.replace(r"[^a-z0-9_]", "", regex=True))
    rename_map = {"4046":"plu4046","4225":"plu4225","4770":"plu4770",
                  "smallbags":"smal_bags","largebags":"large_bags",
                  "xlargebags":"xlarge_bags","totalbags":"total_bags",
                  "totalvolume":"total_volume","averageprice":"average_price"}
    avocado.rename(columns={k:v for k,v in rename_map.items() if k in avocado.columns}, inplace=True)
    avocado["date"]         = pd.to_datetime(avocado["date"])
    avocado["year"]         = avocado["date"].dt.year
    avocado["month"]        = avocado["date"].dt.month
    avocado["month_name"]   = avocado["date"].dt.month_name()
    avocado["quarter"]      = avocado["date"].dt.quarter
    avocado["week_of_year"] = avocado["date"].dt.isocalendar().week.astype(int)
    avocado["revenue"]      = avocado["average_price"] * avocado["total_volume"]
    return avocado

print("Loading data…")
avocado = load_data()
print(f"✅ {len(avocado):,} rows loaded")

YEARS   = sorted(avocado["year"].unique())
REGIONS = sorted([r for r in avocado["region"].unique() if r != "TotalUS"])

# ── PALETTE ───────────────────────────────────────────────────────────────────
NAV      = "#0a1628"   # deep navy
NAV2     = "#112240"   # mid navy
GOLD     = "#c9a84c"   # gold accent
GOLD_LT  = "#e8c97a"   # light gold
CREAM    = "#f5f0e8"   # warm cream background
CONV_C   = "#4a90d9"   # conventional — steel blue
ORG_C    = "#c9a84c"   # organic — gold
TEXT_D   = "#1a2744"   # dark text
TEXT_M   = "#5a6a8a"   # muted text

COLORS   = {"conventional": CONV_C, "organic": ORG_C}

MONTH_ORDER = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]

# ── PLOTLY TEMPLATE ───────────────────────────────────────────────────────────
TMPL = go.layout.Template()
TMPL.layout = go.Layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Georgia, 'Times New Roman', serif", color=TEXT_D),
    xaxis=dict(gridcolor="#e8e4dc", linecolor="#d0c8b8", zeroline=False),
    yaxis=dict(gridcolor="#e8e4dc", linecolor="#d0c8b8", zeroline=False),
    legend=dict(bgcolor="rgba(255,255,255,0.7)", bordercolor="#d0c8b8", borderwidth=1),
    colorway=[CONV_C, ORG_C, "#e07b54", "#6abf8a", "#9b72cf"],
)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def card(children, className="", style=None):
    base = {"background":"white","borderRadius":"12px",
            "boxShadow":"0 2px 12px rgba(10,22,40,0.10)",
            "padding":"24px","marginBottom":"20px"}
    if style: base.update(style)
    return html.Div(children, className=className, style=base)

def kpi(label, value, delta=None):
    return html.Div([
        html.Div(label, style={"fontSize":"0.72rem","fontWeight":"600","letterSpacing":"0.08em",
                               "textTransform":"uppercase","color":TEXT_M,"marginBottom":"6px"}),
        html.Div(value, style={"fontSize":"1.9rem","fontWeight":"700","color":NAV,
                               "fontFamily":"Georgia, serif","lineHeight":"1"}),
        html.Div(delta, style={"fontSize":"0.8rem","color":GOLD,"marginTop":"4px","fontWeight":"600"}) if delta else None,
    ], style={"background":"white","borderRadius":"12px","padding":"20px 24px",
              "boxShadow":"0 2px 12px rgba(10,22,40,0.10)",
              "borderTop":f"3px solid {GOLD}"})

# ── KPI VALUES ────────────────────────────────────────────────────────────────
def compute_kpis(df):
    conv = df[(df["region"]=="TotalUS")&(df["type"]=="conventional")]
    org  = df[(df["region"]=="TotalUS")&(df["type"]=="organic")]
    median_p  = df["average_price"].median()
    premium   = org["average_price"].mean() - conv["average_price"].mean()
    top_reg   = (df[df["region"]!="TotalUS"]
                 .groupby("region")["revenue"].sum().idxmax())
    peak_mon  = (df[df["region"]=="TotalUS"]
                 .groupby("month_name")["total_volume"].mean().idxmax())
    org_15    = org[org["year"]==org["year"].min()]["total_volume"].sum()
    org_21    = org[org["year"]==2021]["total_volume"].sum()
    org_gr    = ((org_21-org_15)/org_15*100) if org_15>0 else 0
    return dict(median_price=f"${median_p:.2f}", organic_premium=f"+${premium:.2f}",
                top_region=top_reg, peak_month=peak_mon, org_growth=f"+{org_gr:.0f}%")

# ── EXTERNAL FONTS ────────────────────────────────────────────────────────────
EXT_CSS = [
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap"
]

app = dash.Dash(__name__, external_stylesheets=EXT_CSS,
                suppress_callback_exceptions=True,
                meta_tags=[{"name":"viewport","content":"width=device-width, initial-scale=1"}])
app.title = "Avocado Sales Dashboard"
server = app.server  # required for gunicorn / Render

# ── GLOBAL FILTER BAR ─────────────────────────────────────────────────────────
filter_bar = card([
    dbc.Row([
        dbc.Col([
            html.Label("Year Range", style={"fontWeight":"600","fontSize":"0.78rem",
                                            "letterSpacing":"0.06em","textTransform":"uppercase",
                                            "color":TEXT_M,"marginBottom":"8px"}),
            dcc.RangeSlider(id="g-years", min=YEARS[0], max=YEARS[-1], step=1,
                            marks={y:str(y) for y in YEARS},
                            value=[YEARS[0], YEARS[-1]],
                            tooltip={"placement":"bottom"},
                            className="gold-slider"),
        ], md=6),
        dbc.Col([
            html.Label("Type", style={"fontWeight":"600","fontSize":"0.78rem",
                                      "letterSpacing":"0.06em","textTransform":"uppercase",
                                      "color":TEXT_M,"marginBottom":"8px"}),
            dbc.Checklist(id="g-types",
                          options=[{"label":" Conventional","value":"conventional"},
                                   {"label":" Organic",     "value":"organic"}],
                          value=["conventional","organic"], inline=True,
                          inputStyle={"marginRight":"5px","accentColor":GOLD}),
        ], md=3),
        dbc.Col([
            html.Label("Region", style={"fontWeight":"600","fontSize":"0.78rem",
                                        "letterSpacing":"0.06em","textTransform":"uppercase",
                                        "color":TEXT_M,"marginBottom":"8px"}),
            dcc.Dropdown(id="g-region",
                         options=[{"label":"All Regions","value":"ALL"}] +
                                 [{"label":r,"value":r} for r in REGIONS],
                         value="ALL", clearable=False,
                         style={"fontSize":"0.85rem"}),
        ], md=3),
    ]),
], style={"marginBottom":"0","borderRadius":"0","boxShadow":"none",
          "borderBottom":f"1px solid #e8e4dc","background":CREAM,"padding":"20px 32px"})

# ── TABS ──────────────────────────────────────────────────────────────────────
tab_style = {"padding":"10px 24px","fontSize":"0.82rem","fontWeight":"600",
             "letterSpacing":"0.05em","textTransform":"uppercase",
             "color":TEXT_M,"border":"none","borderBottom":"3px solid transparent",
             "background":"transparent","cursor":"pointer"}
tab_sel   = {**tab_style,"color":NAV,"borderBottom":f"3px solid {GOLD}"}

tabs = dcc.Tabs(id="main-tabs", value="overview",
    children=[
        dcc.Tab(label="Overview",        value="overview",    style=tab_style, selected_style=tab_sel),
        dcc.Tab(label="Seasonality",     value="season",      style=tab_style, selected_style=tab_sel),
        dcc.Tab(label="Regional",        value="regional",    style=tab_style, selected_style=tab_sel),
        dcc.Tab(label="Holiday Spikes",  value="holidays",    style=tab_style, selected_style=tab_sel),
        dcc.Tab(label="Executive Brief", value="exec",        style=tab_style, selected_style=tab_sel),
    ],
    style={"background":CREAM,"borderBottom":f"1px solid #e0dbd0",
           "paddingLeft":"20px","fontFamily":"DM Sans, sans-serif"},
)

# ── LAYOUT ────────────────────────────────────────────────────────────────────
app.layout = html.Div([

    # ── HEADER ────────────────────────────────────────────────────────────────
    html.Div([
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span("🥑", style={"fontSize":"1.8rem","marginRight":"12px"}),
                        html.Span("Avocado Sales Dashboard",
                                  style={"fontFamily":"Cormorant Garamond, Georgia, serif",
                                         "fontSize":"1.6rem","fontWeight":"700",
                                         "color":"white","letterSpacing":"0.02em"}),
                    ], style={"display":"flex","alignItems":"center"}),
                    html.Div("GreenGrocer · Strategic Intelligence · 2015–2023",
                             style={"color":GOLD_LT,"fontSize":"0.75rem",
                                    "letterSpacing":"0.12em","marginTop":"4px",
                                    "fontFamily":"DM Sans, sans-serif","fontWeight":"300"}),
                ]),
                dbc.Col([
                    html.Div(id="kpi-bar", style={"display":"flex","gap":"24px","justifyContent":"flex-end"}),
                ], style={"display":"flex","alignItems":"center"}),
            ], align="center"),
        ], fluid=True),
    ], style={"background":f"linear-gradient(135deg, {NAV} 0%, {NAV2} 100%)",
              "padding":"20px 32px","boxShadow":"0 4px 20px rgba(10,22,40,0.3)"}),

    filter_bar,
    tabs,

    # ── TAB CONTENT ───────────────────────────────────────────────────────────
    html.Div(id="tab-content",
             style={"background":CREAM,"minHeight":"80vh","padding":"28px 32px",
                    "fontFamily":"DM Sans, sans-serif"}),

], style={"fontFamily":"DM Sans, sans-serif","background":CREAM,"minHeight":"100vh"})


# ── SHARED FILTER HELPER ──────────────────────────────────────────────────────
def filter_df(years, types, region):
    if not types: types = ["conventional","organic"]
    df = avocado[avocado["year"].between(years[0], years[1]) &
                 avocado["type"].isin(types)]
    if region and region != "ALL":
        df = df[df["region"] == region]
    return df


# ── CALLBACK: KPI BAR ─────────────────────────────────────────────────────────
@app.callback(Output("kpi-bar","children"),
              Input("g-years","value"), Input("g-types","value"), Input("g-region","value"))
def update_kpis(years, types, region):
    df = filter_df(years, types, region)
    k  = compute_kpis(df)
    def mini_kpi(label, value):
        return html.Div([
            html.Div(label, style={"color":GOLD_LT,"fontSize":"0.65rem","letterSpacing":"0.08em",
                                   "textTransform":"uppercase","fontWeight":"500"}),
            html.Div(value, style={"color":"white","fontSize":"1.15rem","fontWeight":"700",
                                   "fontFamily":"Cormorant Garamond, serif"}),
        ], style={"textAlign":"center","minWidth":"90px"})
    return [
        mini_kpi("Median Price",    k["median_price"]),
        mini_kpi("Organic Premium", k["organic_premium"]),
        mini_kpi("Top Region",      k["top_region"]),
        mini_kpi("Peak Month",      k["peak_month"]),
        mini_kpi("Organic Growth",  k["org_growth"]),
    ]


# ── CALLBACK: TAB CONTENT ─────────────────────────────────────────────────────
@app.callback(Output("tab-content","children"),
              Input("main-tabs","value"),
              Input("g-years","value"), Input("g-types","value"), Input("g-region","value"))
def render_tab(tab, years, types, region):
    df = filter_df(years, types, region)

    # ── OVERVIEW TAB ──────────────────────────────────────────────────────────
    if tab == "overview":
        # Annual price trend
        annual = df.groupby(["year","type"])["average_price"].mean().reset_index()
        fig_annual = px.line(annual, x="year", y="average_price", color="type",
                             color_discrete_map=COLORS, markers=True, template=TMPL,
                             labels={"year":"Year","average_price":"Avg Price ($)","type":"Type"})
        fig_annual.update_traces(line_width=2.5, marker_size=7)
        fig_annual.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10),
                                 legend=dict(orientation="h",y=1.1,xanchor="right",x=1))

        # Price histogram
        fig_hist = px.histogram(df, x="average_price", color="type",
                                color_discrete_map=COLORS, barmode="overlay",
                                nbins=50, opacity=0.78, template=TMPL,
                                labels={"average_price":"Price ($)","type":"Type"})
        fig_hist.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10),
                               legend=dict(orientation="h",y=1.1,xanchor="right",x=1))

        # Volume by year
        vol = df.groupby(["year","type"])["total_volume"].sum().reset_index()
        fig_vol = px.bar(vol, x="year", y="total_volume", color="type",
                         color_discrete_map=COLORS, barmode="group", template=TMPL,
                         labels={"year":"Year","total_volume":"Volume (lbs)","type":"Type"})
        fig_vol.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10),
                              legend=dict(orientation="h",y=1.1,xanchor="right",x=1))

        return html.Div([
            html.H4("Market Overview", style={"color":NAV,"fontFamily":"Cormorant Garamond, serif",
                                              "fontWeight":"700","marginBottom":"20px","fontSize":"1.5rem"}),
            dbc.Row([
                dbc.Col(card([
                    html.H6("Annual Average Price Trend", style={"color":TEXT_M,"fontSize":"0.78rem",
                            "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"12px"}),
                    dcc.Graph(figure=fig_annual, config={"displayModeBar":False}),
                ]), md=8),
                dbc.Col(card([
                    html.H6("Price Distribution", style={"color":TEXT_M,"fontSize":"0.78rem",
                            "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"12px"}),
                    dcc.Graph(figure=fig_hist, config={"displayModeBar":False}),
                ]), md=4),
            ]),
            dbc.Row([
                dbc.Col(card([
                    html.H6("Total Volume by Year", style={"color":TEXT_M,"fontSize":"0.78rem",
                            "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"12px"}),
                    dcc.Graph(figure=fig_vol, config={"displayModeBar":False}),
                ])),
            ]),
        ])

    # ── SEASONALITY TAB ───────────────────────────────────────────────────────
    elif tab == "season":
        monthly = df.groupby(["month","month_name","type"])["average_price"].mean().reset_index()
        monthly["month_name"] = pd.Categorical(monthly["month_name"], categories=MONTH_ORDER, ordered=True)
        monthly = monthly.sort_values("month_name")

        fig_season = px.line(monthly, x="month_name", y="average_price", color="type",
                             color_discrete_map=COLORS, markers=True, template=TMPL,
                             labels={"month_name":"Month","average_price":"Avg Price ($)","type":"Type"})
        fig_season.update_traces(line_width=2.5, marker_size=8)
        fig_season.update_layout(height=340, margin=dict(l=10,r=10,t=10,b=10),
                                 xaxis_tickangle=-30,
                                 legend=dict(orientation="h",y=1.05,xanchor="right",x=1))
        # add gold band for peak season
        fig_season.add_vrect(x0="June", x1="September",
                             fillcolor=GOLD, opacity=0.08,
                             annotation_text="Peak Season", annotation_position="top left",
                             annotation_font_color=GOLD, annotation_font_size=10)

        # Volume by month
        mon_vol = df.groupby(["month","month_name","type"])["total_volume"].mean().reset_index()
        mon_vol["month_name"] = pd.Categorical(mon_vol["month_name"], categories=MONTH_ORDER, ordered=True)
        mon_vol = mon_vol.sort_values("month_name")
        fig_vol = px.bar(mon_vol, x="month_name", y="total_volume", color="type",
                         color_discrete_map=COLORS, barmode="group", template=TMPL,
                         labels={"month_name":"Month","total_volume":"Avg Volume (lbs)","type":"Type"})
        fig_vol.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10),
                              xaxis_tickangle=-30,
                              legend=dict(orientation="h",y=1.05,xanchor="right",x=1))

        return html.Div([
            html.H4("Seasonal Patterns", style={"color":NAV,"fontFamily":"Cormorant Garamond, serif",
                                                "fontWeight":"700","marginBottom":"20px","fontSize":"1.5rem"}),
            card([
                html.H6("Monthly Average Price — Seasonal Cycle", style={"color":TEXT_M,"fontSize":"0.78rem",
                        "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"4px"}),
                html.P("Prices peak in Q2–Q3 (Jun–Sep) and trough in Q1 — consistent across all 9 years.",
                       style={"fontSize":"0.82rem","color":TEXT_M,"marginBottom":"12px"}),
                dcc.Graph(figure=fig_season, config={"displayModeBar":False}),
            ]),
            card([
                html.H6("Average Volume by Month", style={"color":TEXT_M,"fontSize":"0.78rem",
                        "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"12px"}),
                dcc.Graph(figure=fig_vol, config={"displayModeBar":False}),
            ]),
        ])

    # ── REGIONAL TAB ──────────────────────────────────────────────────────────
    elif tab == "regional":
        df_reg = avocado[avocado["region"]!="TotalUS"]
        if types: df_reg = df_reg[df_reg["type"].isin(types)]
        df_reg = df_reg[df_reg["year"].between(years[0], years[1])]

        # Bubble chart — hero chart
        bubble = (df_reg.groupby(["region","type"])
                  .agg(avg_price=("average_price","mean"),
                       total_volume=("total_volume","sum"),
                       total_revenue=("revenue","sum"))
                  .reset_index())
        top15 = bubble.groupby("region")["total_revenue"].sum().nlargest(15).index.tolist()
        bub = bubble[bubble["region"].isin(top15)]
        top5 = bub.groupby("region")["total_revenue"].sum().nlargest(5).index.tolist()

        fig_bub = px.scatter(bub, x="total_volume", y="avg_price",
                             size="total_revenue", color="type",
                             color_discrete_map=COLORS,
                             hover_name="region",
                             hover_data={"total_revenue":":,.0f","avg_price":":.2f","total_volume":":,.0f"},
                             custom_data=["region"],
                             size_max=65, opacity=0.82, template=TMPL,
                             labels={"total_volume":"Total Volume (lbs)",
                                     "avg_price":"Avg Price ($)","type":"Type"})
        for _, row in bub[bub["region"].isin(top5)].iterrows():
            fig_bub.add_annotation(x=row["total_volume"], y=row["avg_price"],
                                   text=row["region"], showarrow=False,
                                   font=dict(size=9, color=NAV), yshift=12)
        fig_bub.update_layout(height=400, margin=dict(l=10,r=10,t=10,b=10),
                              legend=dict(orientation="h",y=1.02,xanchor="right",x=1))

        # Stacked area — volume growth
        vol_evo = (df_reg.groupby(["year","region","type"])["total_volume"]
                   .sum().reset_index())
        top10_vol = (vol_evo.groupby("region")["total_volume"].sum()
                     .nlargest(10).index.tolist())
        va = (vol_evo[vol_evo["region"].isin(top10_vol)]
              .groupby(["year","region"])["total_volume"].sum().reset_index())
        fig_area = px.area(va, x="year", y="total_volume", color="region",
                           template=TMPL,
                           labels={"year":"Year","total_volume":"Volume (lbs)","region":"Region"})
        fig_area.update_layout(height=360, margin=dict(l=10,r=10,t=10,b=10),
                               legend=dict(orientation="v",yanchor="top",y=1,
                                           xanchor="left",x=1.02,font=dict(size=9)))

        return html.Div([
            html.H4("Regional Analysis", style={"color":NAV,"fontFamily":"Cormorant Garamond, serif",
                                                "fontWeight":"700","marginBottom":"20px","fontSize":"1.5rem"}),
            card([
                html.H6("Price vs Volume vs Revenue — Top 15 Regions", style={"color":TEXT_M,"fontSize":"0.78rem",
                        "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"4px"}),
                html.P("Bubble size = total revenue. Market size outweighs price premium.",
                       style={"fontSize":"0.82rem","color":TEXT_M,"marginBottom":"12px"}),
                dcc.Graph(figure=fig_bub, config={"displayModeBar":False}),
            ]),
            card([
                html.H6("Volume Growth by Region Over Time — Top 10", style={"color":TEXT_M,"fontSize":"0.78rem",
                        "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"4px"}),
                html.P("Organic growth is concentrated in Northeast, Southeast and California.",
                       style={"fontSize":"0.82rem","color":TEXT_M,"marginBottom":"12px"}),
                dcc.Graph(figure=fig_area, config={"displayModeBar":False}),
            ]),
        ])

    # ── HOLIDAY SPIKES TAB ────────────────────────────────────────────────────
    elif tab == "holidays":
        HOLIDAY_META = {
            "Super Bowl":    {"month":2,  "day":7,  "color":"#e74c3c", "week":6},
            "Cinco de Mayo": {"month":5,  "day":5,  "color":GOLD,      "week":18},
            "4th of July":   {"month":7,  "day":4,  "color":"#3498db", "week":27},
            "Thanksgiving":  {"month":11, "day":24, "color":"#8e44ad", "week":47},
        }

        # Weekly volume line
        weekly = (avocado[avocado["region"]=="TotalUS"]
                  .groupby(["date","type"])["total_volume"].sum().reset_index())
        if types: weekly = weekly[weekly["type"].isin(types)]
        weekly = weekly[weekly["date"].dt.year.between(years[0], years[1])]

        fig_line = go.Figure()
        for t in (types or ["conventional","organic"]):
            sub = weekly[weekly["type"]==t].sort_values("date")
            fig_line.add_trace(go.Scatter(
                x=sub["date"], y=sub["total_volume"], mode="lines",
                name=t.capitalize(), line=dict(color=COLORS[t], width=1.5), opacity=0.9))

        for holiday, meta in HOLIDAY_META.items():
            for yr in range(years[0], years[1]+1):
                try:
                    hdate = pd.Timestamp(year=yr, month=meta["month"], day=meta["day"])
                except: continue
                fig_line.add_vline(x=hdate.timestamp()*1000,
                                   line_dash="dash", line_color=meta["color"],
                                   line_width=1.2,
                                   annotation_text=holiday[:5] if yr==years[1] else "",
                                   annotation_font_size=8,
                                   annotation_font_color=meta["color"])

        fig_line.update_layout(template=TMPL, height=340,
                               margin=dict(l=10,r=10,t=20,b=10),
                               legend=dict(orientation="h",y=1.05,xanchor="right",x=1),
                               xaxis_title="Date", yaxis_title="Total Volume (lbs)")

        # Holiday spike bars
        rows = []
        for holiday, meta in HOLIDAY_META.items():
            m, d1, d2 = meta["month"], 1, 14
            for t in (types or ["conventional","organic"]):
                sub = avocado[(avocado["region"]=="TotalUS")&(avocado["type"]==t)&
                              avocado["year"].between(years[0],years[1])]
                mask = (sub["month"]==m)&(sub["date"].dt.day>=d1)&(sub["date"].dt.day<=d2)
                hv = sub[mask]["total_volume"].mean()
                bv = sub[~mask]["total_volume"].mean()
                rows.append({"holiday":holiday,"type":t,
                             "spike_pct":((hv-bv)/bv*100) if bv>0 else 0})
        spike_df = pd.DataFrame(rows)

        fig_spike = px.bar(spike_df, x="holiday", y="spike_pct", color="type",
                           color_discrete_map=COLORS, barmode="group", template=TMPL,
                           labels={"spike_pct":"Volume vs Baseline (%)","holiday":"","type":"Type"})
        fig_spike.add_hline(y=0, line_color=NAV, line_width=1)
        fig_spike.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10),
                                legend=dict(orientation="h",y=1.05,xanchor="right",x=1))

        return html.Div([
            html.H4("Holiday Demand Spikes", style={"color":NAV,"fontFamily":"Cormorant Garamond, serif",
                                                    "fontWeight":"700","marginBottom":"20px","fontSize":"1.5rem"}),
            card([
                html.H6("Weekly National Volume with Holiday Markers", style={"color":TEXT_M,"fontSize":"0.78rem",
                        "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"4px"}),
                html.P("Super Bowl, Cinco de Mayo and 4th of July drive consistent spikes in conventional demand.",
                       style={"fontSize":"0.82rem","color":TEXT_M,"marginBottom":"12px"}),
                dcc.Graph(figure=fig_line, config={"displayModeBar":False}),
            ]),
            card([
                html.H6("Volume Spike vs Baseline by Holiday", style={"color":TEXT_M,"fontSize":"0.78rem",
                        "letterSpacing":"0.07em","textTransform":"uppercase","marginBottom":"4px"}),
                html.P("% difference vs average weekly volume outside the holiday window.",
                       style={"fontSize":"0.82rem","color":TEXT_M,"marginBottom":"12px"}),
                dcc.Graph(figure=fig_spike, config={"displayModeBar":False}),
            ]),
        ])

    # ── EXECUTIVE BRIEF TAB ───────────────────────────────────────────────────
    elif tab == "exec":
        k = compute_kpis(avocado)

        def finding(n, title, text):
            return html.Div([
                html.Div([
                    html.Div(str(n), style={"background":NAV,"color":GOLD,"borderRadius":"50%",
                                           "width":"32px","height":"32px","display":"flex",
                                           "alignItems":"center","justifyContent":"center",
                                           "fontWeight":"700","fontSize":"0.9rem","flexShrink":"0"}),
                    html.Div([
                        html.Div(title, style={"fontWeight":"600","color":NAV,"marginBottom":"4px"}),
                        html.Div(text,  style={"color":TEXT_M,"fontSize":"0.88rem","lineHeight":"1.6"}),
                    ], style={"marginLeft":"14px"}),
                ], style={"display":"flex","alignItems":"flex-start"}),
            ], style={"padding":"16px 0","borderBottom":"1px solid #e8e4dc"})

        def rec(n, title, action, impact):
            colors = [GOLD, "#4a90d9", "#e07b54"]
            return html.Div([
                html.Div(f"0{n}", style={"fontSize":"2.5rem","fontWeight":"700","color":colors[(n-1)%3],
                                         "fontFamily":"Cormorant Garamond, serif",
                                         "lineHeight":"1","marginBottom":"8px"}),
                html.Div(title,  style={"fontWeight":"700","color":NAV,"marginBottom":"8px","fontSize":"1rem"}),
                html.Div([html.Strong("Action: "), action],
                         style={"fontSize":"0.85rem","color":TEXT_M,"marginBottom":"6px"}),
                html.Div([html.Strong("Impact: "), impact],
                         style={"fontSize":"0.85rem","color":TEXT_M}),
            ], style={"background":"white","borderRadius":"12px","padding":"24px",
                      "boxShadow":"0 2px 12px rgba(10,22,40,0.08)",
                      "borderTop":f"3px solid {colors[(n-1)%3]}"})

        return html.Div([
            html.H4("Executive Brief", style={"color":NAV,"fontFamily":"Cormorant Garamond, serif",
                                              "fontWeight":"700","marginBottom":"6px","fontSize":"1.5rem"}),
            html.P("Strategic insights for GreenGrocer · Hass Avocado Board Data 2015–2023",
                   style={"color":TEXT_M,"fontSize":"0.82rem","marginBottom":"24px"}),

            # KPI cards row
            dbc.Row([
                dbc.Col(kpi("Median Price",    k["median_price"]),    md=2, className="mb-3"),
                dbc.Col(kpi("Organic Premium", k["organic_premium"]), md=2, className="mb-3"),
                dbc.Col(kpi("Top Revenue Region", k["top_region"]),   md=3, className="mb-3"),
                dbc.Col(kpi("Peak Month",      k["peak_month"]),      md=3, className="mb-3"),
                dbc.Col(kpi("Organic Growth\n2015→2021", k["org_growth"]), md=2, className="mb-3"),
            ], className="mb-2"),

            dbc.Row([
                # Key findings
                dbc.Col(card([
                    html.H6("Key Findings", style={"color":NAV,"fontWeight":"700",
                                                   "fontFamily":"Cormorant Garamond, serif",
                                                   "fontSize":"1.1rem","marginBottom":"4px"}),
                    finding(1, "Consistent Organic Premium",
                            "Organic avocados command a $0.40–$0.50 premium over conventional across all regions and seasons — suggesting organic consumers are meaningfully price-inelastic."),
                    finding(2, "Predictable Seasonal Pricing",
                            "Prices peak in Q2–Q3 (Aug–Sep) and trough in Q1. This pattern holds across all 9 years, making it a reliable basis for procurement and pricing strategy."),
                    finding(3, "Revenue is Volume-Driven",
                            "West, California and SouthCentral generate the most revenue despite moderate prices. Market size matters more than price premium."),
                    finding(4, "Holiday Demand is Real — for Conventional",
                            "Super Bowl, Cinco de Mayo and 4th of July show consistent spikes exclusively in conventional avocado demand. Organic volumes are holiday-agnostic."),
                    finding(5, "Organic Growth is Structural",
                            "Organic volume nearly tripled from 2015 to 2021. California shows declining conventional volumes alongside growing organic — active consumer switching, not just new demand."),
                ], style={"height":"100%"}), md=7),

                # Recommendations
                dbc.Col([
                    html.H6("Recommendations", style={"color":NAV,"fontWeight":"700",
                                                      "fontFamily":"Cormorant Garamond, serif",
                                                      "fontSize":"1.1rem","marginBottom":"16px"}),
                    rec(1, "Expand Organic Supply in Northeast, Southeast & California",
                        "Increase organic procurement and shelf space ahead of the 2025 season.",
                        "Capture growing organic demand; increase revenue per unit."),
                    html.Div(style={"height":"12px"}),
                    rec(2, "Optimise Holiday Inventory for Conventional",
                        "Increase orders 15–20% before Super Bowl, Cinco de Mayo & 4th of July.",
                        "Reduce waste and stockouts; improve margins and customer satisfaction."),
                    html.Div(style={"height":"12px"}),
                    rec(3, "Implement Dynamic Seasonal Pricing",
                        "Raise prices in Q2–Q3; stimulate demand in Q1 with promotional pricing.",
                        "Maximise revenue during peak seasons while sustaining Q1 volume."),
                ], md=5),
            ]),
        ])

    return html.Div("Select a tab above.")


if __name__ == "__main__":
    app.run(debug=True)
