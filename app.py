import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 페이지 설정
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Chinook Analytics")
PLOTLY_FONT_FAMILY = "Malgun Gothic, AppleGothic, sans-serif"
DB_PATH = "chinook.db"

# -----------------------------------------------------------------------------
# 2. 데이터 로더
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        df_inv = pd.read_sql("""
            SELECT i.InvoiceId, i.InvoiceDate, i.Total, i.BillingCountry,
                   c.CustomerId, c.FirstName || ' ' || c.LastName AS CustomerName,
                   c.Country AS CustomerCountry,
                   e.EmployeeId, e.FirstName || ' ' || e.LastName AS RepName
            FROM invoices i
            JOIN customers c ON i.CustomerId = c.CustomerId
            JOIN employees e ON c.SupportRepId = e.EmployeeId
        """, conn)
        df_inv['InvoiceDate'] = pd.to_datetime(df_inv['InvoiceDate'])
        df_inv['Year'] = df_inv['InvoiceDate'].dt.year
        df_inv['Month'] = df_inv['InvoiceDate'].dt.month
        df_inv['YearMonth'] = df_inv['InvoiceDate'].dt.strftime('%Y-%m')

        df_items = pd.read_sql("""
            SELECT i.InvoiceId, i.InvoiceDate, i.BillingCountry,
                   (ii.UnitPrice * ii.Quantity) AS ItemTotal, ii.Quantity,
                   g.Name AS GenreName, ar.Name AS ArtistName
            FROM invoice_items ii
            JOIN invoices i ON ii.InvoiceId = i.InvoiceId
            JOIN tracks t ON ii.TrackId = t.TrackId
            JOIN genres g ON t.GenreId = g.GenreId
            JOIN albums al ON t.AlbumId = al.AlbumId
            JOIN artists ar ON al.ArtistId = ar.ArtistId
        """, conn)
        df_items['InvoiceDate'] = pd.to_datetime(df_items['InvoiceDate'])
        df_items['Year'] = df_items['InvoiceDate'].dt.year
        conn.close()
        return df_inv, df_items
    except Exception as e:
        st.error(f"DB 오류: {e}")
        return pd.DataFrame(), pd.DataFrame()


# -----------------------------------------------------------------------------
# 3. 고객 관리용 DB 헬퍼
# -----------------------------------------------------------------------------
def get_conn():
    return sqlite3.connect(DB_PATH)

def fetch_customers():
    conn = get_conn()
    df = pd.read_sql("""SELECT CustomerId, FirstName, LastName, Company, Address, City, State,
                               Country, PostalCode, Phone, Fax, Email, SupportRepId
                        FROM customers ORDER BY CustomerId""", conn)
    conn.close()
    return df

def fetch_employees():
    conn = get_conn()
    df = pd.read_sql("""SELECT EmployeeId, FirstName || ' ' || LastName AS Name, Title
                        FROM employees WHERE Title LIKE '%Support%' ORDER BY EmployeeId""", conn)
    conn.close()
    return df

def update_customer(customer_id, data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""UPDATE customers SET FirstName=?, LastName=?, Company=?, Address=?,
                   City=?, State=?, Country=?, PostalCode=?, Phone=?, Fax=?, Email=?,
                   SupportRepId=? WHERE CustomerId=?""",
                (data["FirstName"], data["LastName"], data["Company"], data["Address"],
                 data["City"], data["State"], data["Country"], data["PostalCode"],
                 data["Phone"], data["Fax"], data["Email"], data["SupportRepId"], customer_id))
    conn.commit()
    conn.close()

def insert_customer(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(MAX(CustomerId), 0) + 1 FROM customers")
    new_id = cur.fetchone()[0]
    cur.execute("""INSERT INTO customers (CustomerId, FirstName, LastName, Company, Address,
                   City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (new_id, data["FirstName"], data["LastName"], data["Company"], data["Address"],
                 data["City"], data["State"], data["Country"], data["PostalCode"],
                 data["Phone"], data["Fax"], data["Email"], data["SupportRepId"]))
    conn.commit()
    conn.close()
    return new_id

# -----------------------------------------------------------------------------
# 4. 사이드바 (간소화된 6개 메뉴)
# -----------------------------------------------------------------------------
with st.spinner("데이터 로딩 중..."):
    df_inv, df_items = load_data()
if df_inv.empty or df_items.empty:
    st.stop()

st.sidebar.title("🎵 Chinook Analytics")
menu = st.sidebar.radio(
    "메뉴",
    [
        "📊 KPI 대시보드",
        "💡 비즈니스 인사이트",
        "🌍 국가/고객 분석",
        "🎸 상품/장르 분석",
        "💼 영업사원 성과",
        "👥 고객 관리",
    ],
)

st.sidebar.markdown("---")
st.sidebar.subheader("필터")
min_year, max_year = int(df_inv['Year'].min()), int(df_inv['Year'].max())
selected_years = st.sidebar.slider("연도 범위", min_value=min_year, max_value=max_year, value=(min_year, max_year))
all_countries = sorted(df_inv['BillingCountry'].unique().tolist())
selected_countries = st.sidebar.multiselect("국가 (비워두면 전체)", options=all_countries, default=[])

if selected_countries:
    filtered_inv = df_inv[(df_inv['Year'].between(*selected_years)) & (df_inv['BillingCountry'].isin(selected_countries))]
    filtered_items = df_items[(df_items['Year'].between(*selected_years)) & (df_items['BillingCountry'].isin(selected_countries))]
else:
    filtered_inv = df_inv[df_inv['Year'].between(*selected_years)]
    filtered_items = df_items[df_items['Year'].between(*selected_years)]


# =============================================================================
# 📊 KPI 대시보드 (메인) — 매출 Overview 통합
# =============================================================================
if menu == "📊 KPI 대시보드":
    st.title("📊 KPI 대시보드")
    st.caption("핵심 매출 지표를 한 화면에서 확인합니다. 사이드바 필터에 따라 자동 갱신됩니다.")

    yrs = sorted(filtered_inv['Year'].unique())
    cur_year = yrs[-1] if yrs else max_year
    cur_df = filtered_inv[filtered_inv['Year'] == cur_year]
    prev_df = filtered_inv[filtered_inv['Year'] == cur_year - 1]

    def pct_delta(cur, prev):
        if prev == 0 or pd.isna(prev):
            return None
        return (cur - prev) / prev * 100

    def fmt_delta(v):
        return f"{v:+.1f}%" if v is not None else None

    cur_rev = cur_df['Total'].sum()
    prev_rev = prev_df['Total'].sum()
    cur_orders = cur_df['InvoiceId'].nunique()
    prev_orders = prev_df['InvoiceId'].nunique()
    cur_cust = cur_df['CustomerId'].nunique()
    prev_cust = prev_df['CustomerId'].nunique()
    cur_aov = cur_rev / cur_orders if cur_orders else 0
    prev_aov = prev_rev / prev_orders if prev_orders else 0

    st.markdown(f"##### 🎯 기준 연도: **{cur_year}년** (직전 연도 대비)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💵 총 매출", f"${cur_rev:,.2f}", fmt_delta(pct_delta(cur_rev, prev_rev)))
    k2.metric("🧾 주문 건수", f"{cur_orders:,} 건", fmt_delta(pct_delta(cur_orders, prev_orders)))
    k3.metric("👥 활성 고객", f"{cur_cust:,} 명", fmt_delta(pct_delta(cur_cust, prev_cust)))
    k4.metric("💳 평균 주문액", f"${cur_aov:,.2f}", fmt_delta(pct_delta(cur_aov, prev_aov)))

    st.markdown("---")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📈 월별 매출 추이 + 3개월 이동평균")
        mt = filtered_inv.groupby('YearMonth')['Total'].sum().reset_index().sort_values('YearMonth')
        mt['MA3'] = mt['Total'].rolling(window=3, min_periods=1).mean()
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(x=mt['YearMonth'], y=mt['Total'], name='월 매출', marker_color='#A8DADC'))
        fig_trend.add_trace(go.Scatter(x=mt['YearMonth'], y=mt['MA3'], name='3개월 이동평균',
                                       mode='lines+markers', line=dict(color='#E63946', width=3)))
        fig_trend.update_layout(font_family=PLOTLY_FONT_FAMILY, xaxis_title='연월', yaxis_title='매출($)',
                                legend=dict(orientation='h', y=1.1), height=420)
        st.plotly_chart(fig_trend, use_container_width=True)

    with col2:
        st.subheader("🎯 연간 매출 목표 달성률")

        # 사용자가 직접 목표를 설정할 수 있도록 두 가지 모드 제공
        mode = st.radio(
            "목표 설정 방식",
            ["전년 대비 성장률(%)", "직접 금액 입력($)"],
            horizontal=True,
            key="target_mode",
        )
        if mode == "전년 대비 성장률(%)":
            growth_pct = st.slider("목표 성장률 (%)", min_value=-20, max_value=50, value=10, step=5,
                                   help=f"기준 = 직전 연도({cur_year - 1}) 매출 ${prev_rev:,.0f}")
            base = prev_rev if prev_rev > 0 else cur_rev
            target = base * (1 + growth_pct / 100)
            target_label = f"전년 대비 {growth_pct:+d}%"
        else:
            default_target = float(prev_rev * 1.10) if prev_rev > 0 else float(cur_rev * 1.1)
            target = st.number_input("연간 매출 목표 ($)",
                                     min_value=0.0, value=round(default_target, 2), step=100.0,
                                     help="원하시는 연간 매출 목표를 직접 입력하세요")
            target_label = "사용자 입력 목표"

        achievement = (cur_rev / target * 100) if target > 0 else 0

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=achievement,
            number={'suffix': '%', 'font': {'size': 36}},
            delta={'reference': 100, 'increasing': {'color': '#2A9D8F'},
                   'decreasing': {'color': '#E63946'}},
            title={'text': f"목표: ${target:,.0f}<br><sub>({target_label})</sub>", 'font': {'size': 14}},
            gauge={'axis': {'range': [0, 150]}, 'bar': {'color': '#1D3557'},
                   'steps': [{'range': [0, 70], 'color': '#FFE5E5'},
                             {'range': [70, 100], 'color': '#FFF3B0'},
                             {'range': [100, 150], 'color': '#D8F3DC'}],
                   'threshold': {'line': {'color': 'red', 'width': 4}, 'thickness': 0.85, 'value': 100}}))
        fig_gauge.update_layout(font_family=PLOTLY_FONT_FAMILY, height=360, margin=dict(t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption(f"💡 현재 매출 \\${cur_rev:,.0f} / 목표 \\${target:,.0f} = **{achievement:.1f}%** 달성")

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 연도별 매출 & 전년 대비 성장률(YoY)")
        yearly = filtered_inv.groupby('Year')['Total'].sum().reset_index().sort_values('Year')
        yearly['YoY'] = yearly['Total'].pct_change() * 100
        fig_yoy = go.Figure()
        fig_yoy.add_trace(go.Bar(x=yearly['Year'], y=yearly['Total'], name='매출',
                                 marker_color='#457B9D',
                                 text=[f"${v:,.0f}" for v in yearly['Total']],
                                 textposition='outside'))
        fig_yoy.add_trace(go.Scatter(x=yearly['Year'], y=yearly['YoY'], name='YoY(%)',
                                     yaxis='y2', mode='lines+markers+text',
                                     line=dict(color='#E63946', width=3),
                                     text=[f"{v:+.1f}%" if pd.notna(v) else "" for v in yearly['YoY']],
                                     textposition='top center'))
        fig_yoy.update_layout(font_family=PLOTLY_FONT_FAMILY,
                              xaxis=dict(title='연도', dtick=1),
                              yaxis=dict(title='매출($)'),
                              yaxis2=dict(title='YoY(%)', overlaying='y', side='right'),
                              legend=dict(orientation='h', y=1.1), height=420)
        st.plotly_chart(fig_yoy, use_container_width=True)

    with col2:
        st.subheader("🗓️ 월별 매출 히트맵 (연도 × 월)")
        heat = filtered_inv.pivot_table(index='Month', columns='Year', values='Total', aggfunc='sum').fillna(0)
        fig_heat = px.imshow(heat, text_auto=".0f", aspect="auto",
                             color_continuous_scale="Blues",
                             labels=dict(x="연도", y="월", color="매출($)"))
        fig_heat.update_layout(font_family=PLOTLY_FONT_FAMILY, yaxis=dict(dtick=1), height=420)
        st.plotly_chart(fig_heat, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("🗺️ 국가별 매출 기여도 (Treemap)")
        ct = filtered_inv.groupby('BillingCountry')['Total'].sum().reset_index()
        ct['Total'] = ct['Total'].round(2)
        fig_tree = px.treemap(ct, path=['BillingCountry'], values='Total',
                              color='Total', color_continuous_scale='Blues')
        fig_tree.update_traces(texttemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percentRoot:.1%}',
                               textfont_size=14)
        fig_tree.update_layout(font_family=PLOTLY_FONT_FAMILY, height=420, margin=dict(t=20, l=10, r=10, b=10))
        st.plotly_chart(fig_tree, use_container_width=True)

    with col2:
        st.subheader("📋 핵심 지표 요약")
        avg_m = filtered_inv.groupby('YearMonth')['Total'].sum().mean()
        mxg = filtered_inv.groupby('YearMonth')['Total'].sum().reset_index()
        mxr = mxg.loc[mxg['Total'].idxmax()]
        rr = (filtered_inv.groupby('CustomerId')['InvoiceId'].nunique() > 1).mean() * 100
        summary = pd.DataFrame({
            "지표": ["총 매출", "총 주문 건수", "총 활성 고객 수", "평균 월매출",
                    "최고 매출월", "최고 매출월 매출", "재구매 고객 비율", "고객당 평균 주문 횟수"],
            "값": [f"${filtered_inv['Total'].sum():,.2f}",
                  f"{filtered_inv['InvoiceId'].nunique():,} 건",
                  f"{filtered_inv['CustomerId'].nunique():,} 명",
                  f"${avg_m:,.2f}", str(mxr['YearMonth']),
                  f"${mxr['Total']:,.2f}", f"{rr:.1f}%",
                  f"{filtered_inv['InvoiceId'].nunique() / filtered_inv['CustomerId'].nunique():.2f} 회"]})
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.caption("ℹ️ 모든 지표는 사이드바 필터 적용 후 값입니다.")


# =============================================================================
# 💡 비즈니스 인사이트 (4가지 핵심 인사이트)
# =============================================================================
elif menu == "💡 비즈니스 인사이트":
    st.title("💡 비즈니스 인사이트")
    st.caption("Chinook 데이터 분석을 통해 도출한 4가지 핵심 인사이트와 액션 아이템.")
    st.markdown("---")

    # ① 파레토
    st.header("① 매출은 소수의 국가에 집중되어 있다 (파레토 구조)")
    cv = filtered_inv.groupby('BillingCountry')['Total'].sum().reset_index().sort_values('Total', ascending=False)
    cv['CumPct'] = cv['Total'].cumsum() / cv['Total'].sum() * 100
    fp = go.Figure()
    fp.add_trace(go.Bar(x=cv['BillingCountry'], y=cv['Total'], name='매출($)', marker_color='#4C78A8'))
    fp.add_trace(go.Scatter(x=cv['BillingCountry'], y=cv['CumPct'], name='누적 비율(%)',
                            yaxis='y2', mode='lines+markers',
                            line=dict(color='#E45756', width=3)))
    fp.update_layout(font_family=PLOTLY_FONT_FAMILY,
                     xaxis=dict(title='국가'), yaxis=dict(title='매출($)'),
                     yaxis2=dict(title='누적 비율(%)', overlaying='y', side='right', range=[0, 110]),
                     legend=dict(orientation='h', y=1.1), height=450)
    st.plotly_chart(fp, use_container_width=True)
    top5 = cv.head(5)
    top5_share = top5['Total'].sum() / cv['Total'].sum() * 100
    st.success(
        f"📌 **인사이트:** 상위 5개 국가({', '.join(top5['BillingCountry'].tolist())})가 "
        f"전체 매출의 **{top5_share:.1f}%** 를 차지합니다. "
        f"마케팅 예산을 상위 국가에 집중 투입하면 ROI를 극대화할 수 있습니다."
    )

    st.markdown("---")
    # ② 장르
    st.header("② 'Rock' 장르가 압도적 1위 — 상품 포트폴리오 전략")
    gr = filtered_items.groupby('GenreName')['ItemTotal'].sum().reset_index().sort_values('ItemTotal', ascending=False).head(10)
    fg = px.bar(gr, x='ItemTotal', y='GenreName', orientation='h',
                labels={'ItemTotal': '매출($)', 'GenreName': '장르'},
                color='ItemTotal', color_continuous_scale='Sunset', text='ItemTotal')
    fg.update_traces(texttemplate='$%{text:.0f}', textposition='outside')
    fg.update_layout(font_family=PLOTLY_FONT_FAMILY,
                     yaxis={'categoryorder': 'total ascending'}, height=450)
    st.plotly_chart(fg, use_container_width=True)
    tg = gr.iloc[0]
    tgs = tg['ItemTotal'] / gr['ItemTotal'].sum() * 100
    st.success(
        f"📌 **인사이트:** **{tg['GenreName']}** 장르가 단독으로 상위 10개 장르 매출의 "
        f"**{tgs:.1f}%** 를 차지합니다. Rock 장르 신보 확보·추천 가중치·프로모션 노출 강화로 매출 상승 효과가 큽니다."
    )

    st.markdown("---")
    # ③ 월별 계절성 (편차 차트 제거, 메인 차트만)
    st.header("③ 월별 매출에 계절성이 존재한다 — 프로모션 타이밍")
    monthly = filtered_inv.groupby('Month')['Total'].sum().reset_index()
    monthly['MonthLabel'] = monthly['Month'].apply(lambda m: f"{m}월")
    avg_month = monthly['Total'].mean()
    peak = monthly.loc[monthly['Total'].idxmax()]
    low = monthly.loc[monthly['Total'].idxmin()]

    def classify(row):
        if row['Month'] == int(peak['Month']):
            return '🔥 최고 월'
        if row['Month'] == int(low['Month']):
            return '❄️ 최저 월'
        if row['Total'] >= avg_month:
            return '평균 이상'
        return '평균 이하'

    monthly['Category'] = monthly.apply(classify, axis=1)
    cmap = {'🔥 최고 월': '#E63946', '❄️ 최저 월': '#1D3557',
            '평균 이상': '#52B788', '평균 이하': '#B7E4C7'}
    fm = px.bar(monthly, x='MonthLabel', y='Total', color='Category',
                color_discrete_map=cmap,
                labels={'Total': '매출($)', 'MonthLabel': '월', 'Category': '구분'},
                text='Total',
                category_orders={'Category': ['🔥 최고 월', '평균 이상', '평균 이하', '❄️ 최저 월']})
    fm.update_traces(texttemplate='$%{text:,.0f}', textposition='outside', cliponaxis=False)
    y_min = monthly['Total'].min()
    y_max = monthly['Total'].max()
    pad = (y_max - y_min) * 0.4 if (y_max - y_min) > 0 else 10
    fm.update_yaxes(range=[max(0, y_min - pad), y_max + pad])
    fm.add_hline(y=avg_month, line_dash='dash', line_color='red', line_width=3,
                 annotation_text=f"<b>월 평균 ${avg_month:,.0f}</b>",
                 annotation_position='top right',
                 annotation_font_size=16, annotation_font_color='red',
                 annotation_bgcolor='rgba(255,255,200,0.95)',
                 annotation_bordercolor='red',
                 annotation_borderwidth=1, annotation_borderpad=6)
    fm.update_layout(font_family=PLOTLY_FONT_FAMILY, height=520, margin=dict(t=80, b=40),
                     legend=dict(orientation='h', y=1.12, x=0))
    st.plotly_chart(fm, use_container_width=True)

    diff_pct = (peak['Total'] - low['Total']) / low['Total'] * 100
    st.success(
        f"📌 **인사이트:** 매출 최고 달은 🔥 **{int(peak['Month'])}월(\\${peak['Total']:,.0f})**, "
        f"최저 달은 ❄️ **{int(low['Month'])}월(\\${low['Total']:,.0f})** 으로 "
        f"두 달의 차이는 **\\${peak['Total'] - low['Total']:,.0f} ({diff_pct:.1f}%)** 입니다. "
        f"피크 달 이전에 재고·마케팅을 선제 준비하고, 비수기({int(low['Month'])}월)에는 할인·번들 프로모션을 집중하세요."
    )
    st.caption("ℹ️ 차이를 명확히 보기 위해 Y축 범위를 데이터 근처로 좁혔습니다.")

    st.markdown("---")
    # ④ VIP
    st.header("④ 충성 고객 Top 10 — 이탈 방지가 최우선 과제")
    cu = (filtered_inv.groupby(['CustomerId', 'CustomerName', 'CustomerCountry'])
          .agg(TotalSpent=('Total', 'sum'), OrderCount=('InvoiceId', 'nunique'))
          .reset_index().sort_values('TotalSpent', ascending=False).head(10))
    ftc = px.bar(cu, x='TotalSpent', y='CustomerName', orientation='h',
                 color='CustomerCountry',
                 labels={'TotalSpent': '총 구매액($)', 'CustomerName': '고객명', 'CustomerCountry': '국가'},
                 text='TotalSpent')
    ftc.update_traces(texttemplate='$%{text:.2f}', textposition='outside')
    ftc.update_layout(font_family=PLOTLY_FONT_FAMILY,
                      yaxis={'categoryorder': 'total ascending'}, height=500)
    st.plotly_chart(ftc, use_container_width=True)
    t10s = cu['TotalSpent'].sum() / filtered_inv['Total'].sum() * 100
    st.success(
        f"📌 **인사이트:** 상위 10명의 VIP 고객이 전체 매출의 **{t10s:.1f}%** 를 차지합니다. "
        f"리텐션(이탈 방지) 프로그램 투자가 신규 고객 획득보다 비용 대비 효과가 큽니다."
    )


# =============================================================================
# 🌍 국가/고객 분석 (인사이트의 파레토와 중복되지 않는 detail 분석)
# =============================================================================
elif menu == "🌍 국가/고객 분석":
    st.title("🌍 국가/고객 분석")
    st.caption("국가별 고객 행동 패턴과 전체 고객 리스트를 살펴봅니다.")

    st.subheader("국가별 고객 수 vs 평균 주문액 (버블 크기 = 총 매출)")
    cs = filtered_inv.groupby('BillingCountry').agg(
        CustomerCount=('CustomerId', 'nunique'),
        AvgOrderValue=('Total', 'mean'),
        TotalRevenue=('Total', 'sum')
    ).reset_index()
    fig_sc = px.scatter(cs, x='CustomerCount', y='AvgOrderValue', size='TotalRevenue',
                        hover_name='BillingCountry', color='BillingCountry',
                        labels={'CustomerCount': '고객 수(명)', 'AvgOrderValue': '평균 주문액($)'},
                        height=500)
    fig_sc.update_layout(font_family=PLOTLY_FONT_FAMILY, showlegend=False)
    st.plotly_chart(fig_sc, use_container_width=True)
    st.caption("💡 우상단(고객도 많고 객단가도 높은 국가)이 핵심 시장. 좌상단(고객은 적지만 객단가 높음)은 프리미엄 타겟팅 후보.")

    st.markdown("---")
    st.subheader("📋 고객별 총 구매액 전체 순위")
    cr = filtered_inv.groupby(['CustomerName', 'CustomerCountry']).agg(
        TotalSpent=('Total', 'sum'),
        OrderCount=('InvoiceId', 'nunique')
    ).reset_index().sort_values('TotalSpent', ascending=False)
    cr['TotalSpent'] = cr['TotalSpent'].apply(lambda x: f"${x:,.2f}")
    cr.columns = ['고객명', '국가', '총 구매액', '주문 횟수']
    st.dataframe(cr, use_container_width=True, hide_index=True, height=400)


# =============================================================================
# 🎸 상품/장르 분석 (인사이트의 Rock 차트와 중복되지 않는 시간/아티스트 분석)
# =============================================================================
elif menu == "🎸 상품/장르 분석":
    st.title("🎸 상품/장르 분석")
    st.caption("장르의 시간적 변화와 인기 아티스트를 살펴봅니다.")

    st.subheader("연도별 장르 매출 트렌드 (Top 7 장르)")
    gt = filtered_items.groupby(['Year', 'GenreName'])['ItemTotal'].sum().reset_index()
    top_g = gt.groupby('GenreName')['ItemTotal'].sum().nlargest(7).index
    gt.loc[~gt['GenreName'].isin(top_g), 'GenreName'] = 'Others'
    gt = gt.groupby(['Year', 'GenreName'])['ItemTotal'].sum().reset_index()
    fig_area = px.area(gt, x='Year', y='ItemTotal', color='GenreName',
                       labels={'ItemTotal': '매출($)', 'Year': '연도'}, height=450)
    fig_area.update_layout(font_family=PLOTLY_FONT_FAMILY, xaxis=dict(dtick=1))
    st.plotly_chart(fig_area, use_container_width=True)
    st.caption("💡 장르별 매출이 시간이 지나며 어떻게 변하는지 확인할 수 있습니다.")

    st.markdown("---")
    st.subheader("🎤 인기 아티스트 Top 15 (매출 기준)")
    ar = filtered_items.groupby('ArtistName')['ItemTotal'].sum().reset_index().sort_values('ItemTotal', ascending=False).head(15)
    fig_ar = px.bar(ar, x='ArtistName', y='ItemTotal',
                    labels={'ArtistName': '아티스트', 'ItemTotal': '매출($)'},
                    color='ItemTotal', color_continuous_scale="Teal",
                    text='ItemTotal', height=500)
    fig_ar.update_traces(texttemplate='$%{text:.0f}', textposition='outside')
    fig_ar.update_layout(font_family=PLOTLY_FONT_FAMILY,
                         xaxis={'categoryorder': 'total descending'},
                         coloraxis_showscale=False)
    st.plotly_chart(fig_ar, use_container_width=True)


# =============================================================================
# 💼 영업사원 성과
# =============================================================================
elif menu == "💼 영업사원 성과":
    st.title("💼 영업사원 성과 분석")
    st.caption("Support Rep별 매출·주문·고객 수 비교와 상세 분석.")

    rs = filtered_inv.groupby('RepName').agg(
        TotalRevenue=('Total', 'sum'),
        OrderCount=('InvoiceId', 'nunique'),
        CustomerCount=('CustomerId', 'nunique')
    ).reset_index()

    st.subheader("담당자별 종합 성과 비교")
    rm = rs.melt(id_vars='RepName', var_name='Metric', value_name='Value')
    mm = {'TotalRevenue': '총 매출($)', 'OrderCount': '주문 수', 'CustomerCount': '고객 수'}
    rm['Metric'] = rm['Metric'].map(mm)
    fig_r = px.bar(rm, x='RepName', y='Value', color='Metric', barmode='group',
                   labels={'RepName': '영업사원명', 'Value': '수치'}, height=420)
    fig_r.update_layout(font_family=PLOTLY_FONT_FAMILY)
    st.plotly_chart(fig_r, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("담당자별 월별 매출 추이")
        rt = filtered_inv.groupby(['YearMonth', 'RepName'])['Total'].sum().reset_index()
        fig_rt = px.line(rt, x='YearMonth', y='Total', color='RepName', markers=True,
                         labels={'Total': '매출($)', 'YearMonth': '연월'}, height=420)
        fig_rt.update_layout(font_family=PLOTLY_FONT_FAMILY)
        st.plotly_chart(fig_rt, use_container_width=True)
    with col2:
        st.subheader("담당자별 고객 국가 분포")
        rc = filtered_inv.drop_duplicates(subset=['CustomerId']).groupby(['RepName', 'CustomerCountry']).size().reset_index(name='CustomerCount')
        fig_rc = px.bar(rc, x='RepName', y='CustomerCount', color='CustomerCountry',
                        labels={'RepName': '영업사원명', 'CustomerCount': '고객 수(명)'},
                        text='CustomerCountry', height=420)
        fig_rc.update_layout(font_family=PLOTLY_FONT_FAMILY, barmode='stack')
        st.plotly_chart(fig_rc, use_container_width=True)


# =============================================================================
# 👥 고객 관리 (CRUD)
# =============================================================================
elif menu == "👥 고객 관리":
    st.title("👥 고객 관리")
    st.caption("customers 테이블의 고객 정보를 조회, 수정, 신규 등록할 수 있습니다.")

    tab_view, tab_edit, tab_add = st.tabs(["📋 조회", "✏️ 수정", "➕ 신규 추가"])

    with tab_view:
        st.subheader("고객 목록")
        cdf = fetch_customers()
        c1, c2 = st.columns([2, 2])
        keyword = c1.text_input("🔍 이름 / 이메일 / 회사명 검색", "")
        country_filter = c2.selectbox("국가 필터",
            ["(전체)"] + sorted(cdf['Country'].dropna().unique().tolist()))
        vd = cdf.copy()
        if keyword:
            mask = (vd['FirstName'].str.contains(keyword, case=False, na=False)
                    | vd['LastName'].str.contains(keyword, case=False, na=False)
                    | vd['Email'].str.contains(keyword, case=False, na=False)
                    | vd['Company'].fillna('').str.contains(keyword, case=False, na=False))
            vd = vd[mask]
        if country_filter != "(전체)":
            vd = vd[vd['Country'] == country_filter]
        st.info(f"총 **{len(vd):,}** 명 검색됨 (전체 {len(cdf):,}명)")
        st.dataframe(vd, use_container_width=True, hide_index=True)

    with tab_edit:
        st.subheader("기존 고객 정보 수정")
        cdf = fetch_customers()
        edf = fetch_employees()
        cdf['Label'] = cdf.apply(
            lambda r: f"#{r['CustomerId']} - {r['FirstName']} {r['LastName']} ({r['Email']})", axis=1)
        sel = st.selectbox("수정할 고객 선택", cdf['Label'].tolist())
        sid = int(sel.split(" - ")[0].replace("#", ""))
        row = cdf[cdf['CustomerId'] == sid].iloc[0]

        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            fn = c1.text_input("이름 *", row['FirstName'] or "")
            ln = c2.text_input("성 *", row['LastName'] or "")
            cm = st.text_input("회사", row['Company'] or "")
            ad = st.text_input("주소", row['Address'] or "")
            c3, c4, c5 = st.columns(3)
            ci = c3.text_input("도시", row['City'] or "")
            sa = c4.text_input("주/도", row['State'] or "")
            co = c5.text_input("국가", row['Country'] or "")
            c6, c7 = st.columns(2)
            po = c6.text_input("우편번호", row['PostalCode'] or "")
            ph = c7.text_input("전화", row['Phone'] or "")
            c8, c9 = st.columns(2)
            fx = c8.text_input("팩스", row['Fax'] or "")
            em = c9.text_input("이메일 *", row['Email'] or "")

            eo = edf['EmployeeId'].tolist()
            el = {r['EmployeeId']: f"#{r['EmployeeId']} - {r['Name']} ({r['Title']})"
                  for _, r in edf.iterrows()}
            cr = int(row['SupportRepId']) if pd.notna(row['SupportRepId']) else eo[0]
            sr = st.selectbox("담당 영업사원", eo,
                              index=eo.index(cr) if cr in eo else 0,
                              format_func=lambda x: el.get(x, str(x)))

            if st.form_submit_button("💾 정보 업데이트", type="primary"):
                if not fn or not ln or not em:
                    st.error("이름, 성, 이메일은 필수 항목입니다.")
                else:
                    try:
                        update_customer(sid, {
                            "FirstName": fn, "LastName": ln,
                            "Company": cm or None, "Address": ad or None,
                            "City": ci or None, "State": sa or None,
                            "Country": co or None, "PostalCode": po or None,
                            "Phone": ph or None, "Fax": fx or None,
                            "Email": em, "SupportRepId": int(sr)})
                        st.success(f"✅ CustomerId #{sid} 정보 업데이트 완료.")
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"오류: {e}")

    with tab_add:
        st.subheader("신규 고객 등록")
        edf = fetch_employees()
        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            fn = c1.text_input("이름 *")
            ln = c2.text_input("성 *")
            cm = st.text_input("회사")
            ad = st.text_input("주소")
            c3, c4, c5 = st.columns(3)
            ci = c3.text_input("도시")
            sa = c4.text_input("주/도")
            co = c5.text_input("국가")
            c6, c7 = st.columns(2)
            po = c6.text_input("우편번호")
            ph = c7.text_input("전화")
            c8, c9 = st.columns(2)
            fx = c8.text_input("팩스")
            em = c9.text_input("이메일 *")

            eo = edf['EmployeeId'].tolist()
            el = {r['EmployeeId']: f"#{r['EmployeeId']} - {r['Name']} ({r['Title']})"
                  for _, r in edf.iterrows()}
            sr = st.selectbox("담당 영업사원", eo,
                              format_func=lambda x: el.get(x, str(x)))

            if st.form_submit_button("➕ 신규 고객 등록", type="primary"):
                if not fn or not ln or not em:
                    st.error("이름, 성, 이메일은 필수 항목입니다.")
                else:
                    try:
                        nid = insert_customer({
                            "FirstName": fn, "LastName": ln,
                            "Company": cm or None, "Address": ad or None,
                            "City": ci or None, "State": sa or None,
                            "Country": co or None, "PostalCode": po or None,
                            "Phone": ph or None, "Fax": fx or None,
                            "Email": em, "SupportRepId": int(sr)})
                        st.success(f"✅ 신규 고객 등록 완료. (CustomerId: #{nid})")
                        st.balloons()
                        st.cache_data.clear()
                    except Exception as e:
                        st.error(f"오류: {e}")
