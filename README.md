# 🎵 Chinook 데이터 분석 대시보드

Chinook 샘플 데이터베이스(가상의 디지털 음원 판매 회사)를 활용하여 **Streamlit**으로 만든
인터랙티브 분석 대시보드입니다. **6개의 명확한 메뉴**로 구성되어 있으며, 각 페이지는
중복 없이 고유한 분석 관점을 제공합니다.

- 💻 GitHub: https://github.com/respect0098-prog/web_site_test_project
- 🌐 사이트 주소: *(Streamlit Cloud 배포 후 추가 예정)*

---

## 📑 메뉴 구성 (총 6개)

| 메뉴 | 역할 | 핵심 차트 |
|------|------|----------|
| 📊 KPI 대시보드 | **메인 모니터링 화면**. 핵심 지표·트렌드·성과 한눈에 | KPI 카드, 이동평균, 게이지, YoY, 히트맵, Treemap, 요약 표 |
| 💡 비즈니스 인사이트 | **4가지 핵심 발견사항**과 액션 아이템 | 파레토, 장르 Top10, 월별 계절성, VIP Top10 |
| 🌍 국가/고객 분석 | 국가별 고객 행동 패턴 + 전체 고객 리스트 | 산점도, 검색 가능한 고객 테이블 |
| 🎸 상품/장르 분석 | 장르의 시간적 변화 + 인기 아티스트 | 장르 트렌드(영역), 아티스트 Top15 |
| 💼 영업사원 성과 | Support Rep별 성과 비교 | 종합 비교, 월별 추이, 국가 분포 |
| 👥 고객 관리 | customers 테이블 **CRUD** | 조회 / 수정 / 신규 등록 탭 |

> 🧹 **간결성을 위해 정리된 항목**: 매출 Overview 페이지(KPI 대시보드와 통합), 국가별 매출 Top10(인사이트와 중복), 장르 도넛(인사이트와 중복), 평균 대비 편차 차트(가독성 저하).

---

## 💡 (1) 시각화를 통해 도출한 비즈니스 인사이트

「💡 비즈니스 인사이트」 페이지에 4가지 인사이트가 시각화와 함께 제공됩니다.

### ① 매출은 소수의 국가에 집중되어 있다 — 파레토 구조
- **시각화**: 국가별 매출 막대 + 누적 비율(%) 라인 (Pareto Chart)
- **발견**: 상위 5개 국가(USA, Canada, France, Brazil, Germany 등)가 전체 매출의 **약 50% 이상**을 차지합니다.
- **시사점**: 마케팅 예산을 상위 국가에 집중 투입하면 ROI가 극대화되며, 매출 비중이
  낮은 국가는 "선택과 집중" 또는 디지털 전용 채널 전환을 검토합니다.

### ② Rock 장르가 압도적 1위 — 상품 포트폴리오 전략
- **시각화**: 장르별 매출 Top 10 가로 막대 차트 (값 라벨 포함)
- **발견**: **Rock** 장르 단독으로 상위 10개 장르 매출의 **약 35~40%** 를 차지하며,
  Latin / Metal / Alternative & Punk가 그 뒤를 잇습니다.
- **시사점**: Rock 장르의 신보 확보·추천 알고리즘 가중치·홈 화면 노출을 강화하면
  매출 상승 효과가 큽니다. 2·3위 장르는 보조 전략군으로 관리합니다.

### ③ 월별 매출에 계절성이 존재한다 — 프로모션 타이밍
- **시각화**: 월별 매출 막대(최고/최저/평균이상/평균이하 4단계 색상 구분) + 월 평균선
- **발견**: 최고 월과 최저 월의 매출 차이가 약 8% 발생합니다. 막대 위에 정확한 매출액을
  표시하고 Y축 범위를 데이터 근처로 좁혀 차이를 시각적으로 강조했습니다.
- **시사점**: 피크 달 1~2개월 전 재고·마케팅을 선제 준비하고, 비수기에는 할인 쿠폰·번들
  프로모션을 집중시켜 연중 매출 변동성을 줄입니다.

### ④ 충성 고객 Top 10 — 이탈 방지가 최우선
- **시각화**: VIP 고객 Top 10 가로 막대 (국가별 색상 구분)
- **발견**: 상위 10명의 VIP 고객이 전체 매출의 약 15~20%를 차지합니다.
- **시사점**: 신규 고객 획득(CAC)보다 **리텐션(이탈 방지)** 투자 효율이 훨씬 높습니다.
  VIP 전용 할인, 1:1 CS 응대, 개인화 추천 등 로열티 프로그램을 우선 강화합니다.

---

## 🗄️ (2) 대시보드에 사용된 SQL 구문 설명

`app.py`에서 사용한 주요 SQL 쿼리와 그 역할을 정리했습니다.

### ① 인보이스(매출) 통합 조회 — `load_data()` 내부
```sql
SELECT i.InvoiceId, i.InvoiceDate, i.Total, i.BillingCountry,
       c.CustomerId, c.FirstName || ' ' || c.LastName AS CustomerName,
       c.Country AS CustomerCountry,
       e.EmployeeId, e.FirstName || ' ' || e.LastName AS RepName
FROM invoices i
JOIN customers c ON i.CustomerId = c.CustomerId
JOIN employees e ON c.SupportRepId = e.EmployeeId;
```
- `invoices`(주문) ↔ `customers`(고객) ↔ `employees`(직원) 3개 테이블을 JOIN.
- **KPI 대시보드, 국가/고객 분석, 영업사원 성과, 인사이트 ①·③·④** 페이지의 데이터 소스.
- `||` 연산자로 FirstName과 LastName을 합쳐 고객명·영업사원명을 생성합니다.

### ② 아이템(상품) 단위 조회 — `load_data()` 내부
```sql
SELECT i.InvoiceId, i.InvoiceDate, i.BillingCountry,
       (ii.UnitPrice * ii.Quantity) AS ItemTotal, ii.Quantity,
       g.Name AS GenreName, ar.Name AS ArtistName
FROM invoice_items ii
JOIN invoices i  ON ii.InvoiceId = i.InvoiceId
JOIN tracks   t  ON ii.TrackId   = t.TrackId
JOIN genres   g  ON t.GenreId    = g.GenreId
JOIN albums   al ON t.AlbumId    = al.AlbumId
JOIN artists  ar ON al.ArtistId  = ar.ArtistId;
```
- `invoice_items` ↔ `tracks` ↔ `genres` ↔ `albums` ↔ `artists` 5개 테이블 JOIN.
- `UnitPrice * Quantity`로 **아이템별 매출(ItemTotal)** 을 계산.
- **상품/장르 분석, 인사이트 ② Rock 장르** 차트의 데이터 소스.

### ③ 고객 목록 조회 — `fetch_customers()`
```sql
SELECT CustomerId, FirstName, LastName, Company, Address, City, State,
       Country, PostalCode, Phone, Fax, Email, SupportRepId
FROM customers
ORDER BY CustomerId;
```
- customers 테이블의 **주요 12개 컬럼**을 가져와 「고객 관리 → 조회」 탭에 표시.

### ④ 영업사원(Support Rep) 목록 — `fetch_employees()`
```sql
SELECT EmployeeId, FirstName || ' ' || LastName AS Name, Title
FROM employees
WHERE Title LIKE '%Support%'
ORDER BY EmployeeId;
```
- 직책에 'Support'가 포함된 직원만 필터링하여 **고객 담당자 드롭다운**에 사용.

### ⑤ 신규 CustomerId 생성 — `insert_customer()`
```sql
SELECT COALESCE(MAX(CustomerId), 0) + 1 FROM customers;
```
- Chinook의 `customers.CustomerId`는 AUTOINCREMENT가 아니므로
  현재 최대값에 +1을 하여 새 ID를 직접 생성합니다.
- `COALESCE`로 테이블이 비어있을 때(NULL)에도 안전하게 1을 반환.

### ⑥ 신규 고객 INSERT — `insert_customer()`
```sql
INSERT INTO customers (CustomerId, FirstName, LastName, Company, Address,
                       City, State, Country, PostalCode, Phone, Fax,
                       Email, SupportRepId)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
```
- 폼 입력값을 **파라미터 바인딩(`?`)** 으로 안전하게 전달하여 SQL Injection을 방지.

### ⑦ 기존 고객 UPDATE — `update_customer()`
```sql
UPDATE customers
SET FirstName = ?, LastName = ?, Company = ?, Address = ?, City = ?,
    State = ?, Country = ?, PostalCode = ?, Phone = ?, Fax = ?,
    Email = ?, SupportRepId = ?
WHERE CustomerId = ?;
```
- 사용자가 선택한 `CustomerId` 한 건만 정확히 수정하도록 `WHERE` 조건을 명시.
- 12개 컬럼 전체를 일괄 갱신.

---

## 🎨 디자인 정리 원칙

이번 정리에서 적용한 원칙입니다.

1. **중복 제거**: 같은 차트가 여러 페이지에 등장하지 않도록 정리.
   - KPI 카드는 KPI 대시보드에만, 파레토는 인사이트에만, 장르 분포는 인사이트에만.
2. **각 페이지의 명확한 역할**: 메인 화면(KPI), 핵심 발견(인사이트), 상세 분석(국가·상품·영업사원), 운영(고객 관리).
3. **가독성 우선**: Y축 범위 자동 조정, 막대 위에 값 라벨, 색상으로 카테고리 구분.
4. **모든 차트는 사이드바 필터(연도·국가)에 자동 반응**.

---

## 🔁 데이터 흐름

```
[사용자 입력] → Streamlit UI
       │
       ▼
[Pandas + SQL] ← chinook.db (SQLite)
       │
       ▼
[Plotly 시각화] / [DB UPDATE·INSERT 반영]
```

- 분석 쿼리는 `@st.cache_data`로 캐싱하여 빠른 응답을 제공.
- 고객 CRUD는 캐시 없이 즉시 실행되며, 작업 후 `st.cache_data.clear()`로 분석 데이터도 함께 갱신.

---

## ▶️ 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 http://localhost:8501 접속.
DB 변경 사항은 **DB Browser for SQLite**로 `chinook.db`의 customers 테이블에서 직접 확인할 수 있습니다.

---

## 🛠️ 사용 기술 스택

- **Python 3.10+**, **Streamlit**, **Pandas**, **Plotly**
- **SQLite (Chinook 샘플 DB)**
