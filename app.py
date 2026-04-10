import streamlit as st
import pandas as pd
import os
import io
import zipfile
from datetime import datetime
from typing import List, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

st.set_page_config(page_title="인증서 다운로드", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "certificates.csv")
FILES_DIR = os.path.join(BASE_DIR, "files")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
STAMP_PATH = os.path.join(ASSETS_DIR, "stamp.png")


def resolve_path(*candidates):
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def setup_fonts() -> tuple[str, str]:
    regular_path = resolve_path(
        os.path.join(ASSETS_DIR, "NanumGothic.ttf"),
        os.path.join(BASE_DIR, "NanumGothic.ttf"),
        "/mnt/data/NanumGothic.ttf",
    )
    bold_path = resolve_path(
        os.path.join(ASSETS_DIR, "NanumGothicBold.ttf"),
        os.path.join(BASE_DIR, "NanumGothicBold.ttf"),
        "/mnt/data/NanumGothicBold.ttf",
    )

    if not regular_path or not bold_path:
        st.error(
            "한글 폰트를 찾지 못했습니다. assets 폴더에 "
            "NanumGothic.ttf, NanumGothicBold.ttf 파일이 있어야 합니다."
        )
        st.stop()

    pdfmetrics.registerFont(TTFont("Nanum", regular_path))
    pdfmetrics.registerFont(TTFont("Nanum-Bold", bold_path))
    return "Nanum", "Nanum-Bold"


PDF_FONT, PDF_FONT_BOLD = setup_fonts()

if not os.path.exists(CSV_PATH):
    st.error("certificates.csv 파일을 찾지 못했습니다.")
    st.stop()

df = pd.read_csv(CSV_PATH)

# 공백 제거 및 기본 정제
if "cert_name" in df.columns:
    df["cert_name"] = df["cert_name"].str.strip()

# 동일 문서 중복 제거
dedupe_cols = ["product_code", "cert_name", "type", "template_type", "file"]
existing_dedupe_cols = [col for col in dedupe_cols if col in df.columns]
if existing_dedupe_cols:
    df = df.drop_duplicates(subset=existing_dedupe_cols, keep="first")


def draw_wrapped_centered_text(c, text, center_x, start_y, max_width, font_name, font_size, line_gap=14):
    c.setFont(font_name, font_size)
    words = str(text).split(" ")
    lines = []
    current = ""

    for word in words:
        test_line = word if current == "" else f"{current} {word}"
        if stringWidth(test_line, font_name, font_size) <= max_width:
            current = test_line
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    total_height = (len(lines) - 1) * line_gap
    y_offset = start_y + (total_height / 2)

    for i, line in enumerate(lines):
        c.drawCentredString(center_x, y_offset - (i * line_gap), line)


def generate_origin_certificate_pdf(
    product_name: str,
    main_ingredient: str = "",
    origin_country: str = "",
    receiver: str = "수신자제위",
) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    today = datetime.today().strftime("%Y-%m-%d")

    def draw_text(x, y, text, size=11, font=PDF_FONT):
        c.setFont(font, size)
        c.drawString(x, y, str(text))

    def draw_center(x, y, text, size=11, font=PDF_FONT):
        c.setFont(font, size)
        c.drawCentredString(x, y, str(text))

    # 외곽 테두리
    c.setLineWidth(0.8)
    c.rect(15, 15, width - 30, height - 30)

    # 상단 헤더 영역 (로고 및 회사명)
    header_top = height - 15
    header_line = height - 70
    
    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 30, height - 55, width=110, height=24, mask="auto")

    # 회사명 상하중앙 정렬 (15~70 사이 정중앙)
    draw_center(width / 2, (header_top + header_line)/2 - 8, "주식회사 삼 양 사", size=22, font=PDF_FONT_BOLD)
    c.line(15, header_line, width - 15, header_line)

    # 주소 영역 상하중앙 정렬
    address_line = height - 95
    draw_center(width / 2, (header_line + address_line)/2 - 3, 
                "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277", 
                size=9.5, font=PDF_FONT)
    c.line(15, address_line, width - 15, address_line)

    # 정보 박스 (발신일자, 수신 등)
    info_top = address_line - 15
    info_height = 110
    info_bottom = info_top - info_height
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    row_gap = 26
    draw_text(35, info_top - 25, "발신일자 :", 11, PDF_FONT_BOLD)
    draw_text(115, info_top - 25, today, 11, PDF_FONT)

    draw_text(35, info_top - 25 - row_gap, "수    신 :", 11, PDF_FONT_BOLD)
    draw_text(115, info_top - 25 - row_gap, receiver or "수신자제위", 11, PDF_FONT)

    draw_text(35, info_top - 25 - row_gap*2, "참    조 :", 11, PDF_FONT_BOLD)

    # 제목 위치 조정 (선이 글자 아래로 가도록)
    draw_text(35, info_top - 25 - row_gap*3, "제    목 :", 11, PDF_FONT_BOLD)
    draw_text(115, info_top - 25 - row_gap*3, "원산지 증명", 11, PDF_FONT)

    # 본문 1번 항목
    body_y = info_bottom - 35
    draw_text(45, body_y, "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어", 11, PDF_FONT)
    # 줄 간격 좁힘 (-20 -> -16)
    draw_text(63, body_y - 16, "주신 각별한 애호에 감사 드립니다.", 11, PDF_FONT)

    draw_text(45, body_y - 55, "2. 귀사에 납품되는 다음 제품의 원료 원산지는 아래와 같습니다.", 11, PDF_FONT)

    # 제품 정보 테이블
    table_top = body_y - 85
    table_height = 85
    table_bottom = table_top - table_height
    x0, x1, x2, x3 = 25, 170, 340, width - 25

    c.rect(x0, table_bottom, x3 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)
    c.line(x2, table_bottom, x2, table_top)

    header_h = 28
    c.line(x0, table_top - header_h, x3, table_top - header_h)
    
    draw_center((x0 + x1) / 2, table_top - 18, "제품명", 11, PDF_FONT_BOLD)
    draw_center((x1 + x2) / 2, table_top - 18, "주원료", 11, PDF_FONT_BOLD)
    draw_center((x2 + x3) / 2, table_top - 18, "원료원산지", 11, PDF_FONT_BOLD)

    content_mid_y = table_bottom + (table_height - header_h) / 2 - 4
    draw_center((x0 + x1) / 2, content_mid_y, product_name, 12, PDF_FONT)
    draw_center((x1 + x2) / 2, content_mid_y, main_ingredient or "-", 11, PDF_FONT)

    draw_wrapped_centered_text(c, origin_country or "-", (x2 + x3) / 2, content_mid_y + 2, 
                               (x3 - x2) - 15, PDF_FONT, 10, line_gap=13)

    draw_text(45, table_bottom - 35, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.", 11, PDF_FONT)
    draw_text(width - 85, 120, "1부.끝.", 11, PDF_FONT)

    # 하단 직인 영역
    footer_y = 95
    draw_center(width / 2, footer_y, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(width / 2, footer_y - 22, "주식회사 삼양사", 13, PDF_FONT_BOLD)
    draw_center(width / 2, footer_y - 44, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 75, footer_y - 65, width=70, height=70, mask="auto")

    # 최하단 서식 정보
    c.line(15, 35, width - 15, 35)
    draw_text(35, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(width - 160, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit UI 및 로직 ---
query_params = st.query_params
product_code = query_params.get("product")

if product_code:
    product_data = df[df["product_code"] == product_code].copy()
    if len(product_data) == 0:
        st.error("해당 제품을 찾을 수 없습니다.")
    else:
        # 중복 방지 로직
        product_data['has_content'] = product_data['file'].notna() | product_data['template_type'].notna()
        product_data = product_data.sort_values(by='has_content', ascending=False)
        product_data = product_data.drop_duplicates(subset=['cert_name'], keep='first')

        product_name = product_data.iloc[0]["product_name"]
        st.title(f"{product_name} 인증서 / 확인서")
        
        all_docs_for_zip = []
        for idx, row in product_data.reset_index(drop=True).iterrows():
            cert_name = str(row["cert_name"])
            doc_type = str(row["type"]).strip().lower()
            
            col1, col2, col3 = st.columns([0.5, 3.5, 1.0])
            
            if doc_type == "template" and str(row.get("template_type")) == "origin":
                pdf_data = generate_origin_certificate_pdf(
                    product_name=product_name,
                    main_ingredient=str(row.get("main_ingredient", "-")),
                    origin_country=str(row.get("origin_country", "-")),
                    receiver=str(row.get("receiver", "수신자제위"))
                )
                file_bytes = pdf_data.getvalue()
                file_name = f"{product_name}_원산지증명서_{datetime.today().strftime('%Y%m%d')}.pdf"
                
                with col1: checked = st.checkbox("", key=f"c_{idx}")
                with col2: st.write(cert_name)
                with col3: st.download_button("다운로드", file_bytes, file_name, "application/pdf", key=f"d_{idx}")
                all_docs_for_zip.append((file_name, file_bytes, checked))
            
            # (기타 파일 및 템플릿 로직 생략 - 필요시 기존 코드 유지)

        if all_docs_for_zip:
            st.divider()
            selected = [(n, b) for n, b, c in all_docs_for_zip if c]
            if selected:
                # ZIP 생성 함수 호출 로직
                pass
else:
    st.title("제품별 인증서 관리")
    # 제품 목록 표시 로직
