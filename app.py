import streamlit as st
import pandas as pd
import os
import io
import zipfile
from datetime import datetime
from typing import List, Tuple, Callable, Union, Dict, Any

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


# -----------------------------
# 기본 유틸
# -----------------------------
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


def build_zip_from_documents(documents: List[Tuple[str, bytes]]) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_bytes in documents:
            zip_file.writestr(file_name, file_bytes)
    zip_buffer.seek(0)
    return zip_buffer


# -----------------------------
# 데이터 로드
# -----------------------------
if not os.path.exists(CSV_PATH):
    st.error("certificates.csv 파일을 찾지 못했습니다.")
    st.stop()

df = pd.read_csv(CSV_PATH)

if "cert_name" in df.columns:
    df["cert_name"] = df["cert_name"].astype(str).str.strip()

dedupe_cols = ["product_code", "cert_name", "type", "template_type", "file"]
existing_dedupe_cols = [col for col in dedupe_cols if col in df.columns]
if existing_dedupe_cols:
    df = df.drop_duplicates(subset=existing_dedupe_cols, keep="first")


# -----------------------------
# PDF 공통 그리기 함수
# -----------------------------
def draw_text(c, x, y, text, size=11, font=PDF_FONT):
    c.setFont(font, size)
    c.drawString(x, y, str(text))


def draw_center(c, x, y, text, size=11, font=PDF_FONT):
    c.setFont(font, size)
    c.drawCentredString(x, y, str(text))


def draw_wrapped_centered_text(
    c,
    text,
    center_x,
    start_y,
    max_width,
    font_name,
    font_size,
    line_gap=14,
):
    """텍스트를 줄바꿈하여 지정된 x축 중앙에 맞춰 그림"""
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


def draw_common_frame(c, width, height):
    c.setLineWidth(0.8)
    c.rect(15, 15, width - 30, height - 30)


def draw_common_header(
    c,
    width,
    height,
    company_name="주식회사 삼양사",
    company_name_spaced=False,
):
    header_top = height - 15
    header_line = height - 70

    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 30, height - 55, width=110, height=24, mask="auto")

    display_name = "주식회사 삼 양 사" if company_name_spaced else company_name
    draw_center(c, width / 2, (header_top + header_line) / 2 - 8, display_name, 22, PDF_FONT_BOLD)
    c.line(15, header_line, width - 15, header_line)

    address_line = height - 95
    draw_center(
        c,
        width / 2,
        (header_line + address_line) / 2 - 3,
        "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277",
        9.5,
        PDF_FONT,
    )
    c.line(15, address_line, width - 15, address_line)

    return address_line


def draw_info_box(c, width, info_top, today, receiver, subject):
    info_height = 110
    info_bottom = info_top - info_height
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    row_gap = 26
    font_size = 11
    num_rows = 4

    text_block_height = font_size + row_gap * (num_rows - 1)
    top_bottom_padding = (info_height - text_block_height) / 2
    start_y = info_top - top_bottom_padding - font_size + 2

    draw_text(c, 35, start_y, "발신일자 :", font_size, PDF_FONT_BOLD)
    draw_text(c, 100, start_y, today, font_size, PDF_FONT)

    draw_text(c, 35, start_y - row_gap, "수    신 :", font_size, PDF_FONT_BOLD)
    draw_text(c, 100, start_y - row_gap, receiver or "수신자제위", font_size, PDF_FONT)

    draw_text(c, 35, start_y - row_gap * 2, "참    조 :", font_size, PDF_FONT_BOLD)

    draw_text(c, 35, start_y - row_gap * 3, "제    목 :", font_size, PDF_FONT_BOLD)
    draw_text(c, 100, start_y - row_gap * 3, subject, font_size, PDF_FONT)

    return info_bottom


def draw_common_footer(c, width):
    footer_y = 115
    draw_center(c, width / 2, footer_y, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(c, width / 2, footer_y - 22, "주식회사 삼양사", 12, PDF_FONT_BOLD)
    draw_center(c, width / 2, footer_y - 44, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 75, footer_y - 65, width=70, height=70, mask="auto")

    c.line(15, 35, width - 15, 35)
    draw_text(c, 32, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(c, width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(c, width - 160, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)


def draw_two_column_table(
    c,
    width,
    table_top,
    headers,
    values,
    left_ratio=0.4,
    x_margin=80,
    table_height=85,
):
    table_bottom = table_top - table_height
    x0 = x_margin
    x2 = width - x_margin
    x1 = x0 + (x2 - x0) * left_ratio

    c.rect(x0, table_bottom, x2 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)

    header_h = 28
    c.line(x0, table_top - header_h, x2, table_top - header_h)

    draw_center(c, (x0 + x1) / 2, table_top - 15, headers[0], 12, PDF_FONT_BOLD)
    draw_center(c, (x1 + x2) / 2, table_top - 15, headers[1], 12, PDF_FONT_BOLD)

    content_mid_y = table_bottom + (table_height - header_h) / 2 - 4
    draw_center(c, (x0 + x1) / 2, content_mid_y, values[0], 12, PDF_FONT)
    draw_center(c, (x1 + x2) / 2, content_mid_y, values[1], 11, PDF_FONT)

    return table_bottom


def draw_three_column_table_for_origin(
    c,
    width,
    table_top,
    product_name,
    main_ingredient,
    origin_country,
    table_height=85,
):
    table_bottom = table_top - table_height
    x0, x1, x2, x3 = 25, 170, 340, width - 25

    c.rect(x0, table_bottom, x3 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)
    c.line(x2, table_bottom, x2, table_top)

    header_h = 28
    c.line(x0, table_top - header_h, x3, table_top - header_h)

    draw_center(c, (x0 + x1) / 2, table_top - 15, "제품명", 12, PDF_FONT_BOLD)
    draw_center(c, (x1 + x2) / 2, table_top - 15, "주원료", 12, PDF_FONT_BOLD)
    draw_center(c, (x2 + x3) / 2, table_top - 15, "원료원산지", 12, PDF_FONT_BOLD)

    content_mid_y = table_bottom + (table_height - header_h) / 2 - 4
    draw_center(c, (x0 + x1) / 2, content_mid_y, product_name, 12, PDF_FONT)
    draw_center(c, (x1 + x2) / 2, content_mid_y, main_ingredient or "-", 11, PDF_FONT)

    draw_wrapped_centered_text(
        c,
        origin_country or "-",
        (x2 + x3) / 2,
        content_mid_y + 2,
        (x3 - x2) - 15,
        PDF_FONT,
        10,
        line_gap=13,
    )

    return table_bottom

def generate_template_pdf(product_name: str, template_type: str) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    today = datetime.today().strftime("%Y-%m-%d")

    title, lines = get_template_lines(product_name, template_type)

    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 50, height - 90, width=140, height=40, mask="auto")

    c.setFont(PDF_FONT_BOLD, 18)
    c.drawCentredString(width / 2, height - 120, title)

    y = height - 180
    line_gap = 24

    c.setFont(PDF_FONT, 11)
    for line in lines:
        if line == "":
            y -= 10
        else:
            c.drawString(70, y, line)
            y -= line_gap

    y -= 20
    c.setFont(PDF_FONT, 11)
    c.drawString(70, y, f"발행일자: {today}")
    y -= line_gap
    c.drawString(70, y, "발행처: 삼양사")
    y -= line_gap
    c.drawString(70, y, "발행부서: 품질 관련 부서")

    y -= 60
    c.drawString(70, y, "상기와 같이 확인합니다.")

    y -= 50
    c.drawString(70, y, "삼양사")
    c.drawString(70, y - 22, "품질책임자: __________________")

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, 220, y - 45, width=80, height=80, mask="auto")

    c.setFont(PDF_FONT, 9)
    c.drawString(70, 50, "본 문서는 시스템에서 자동 생성되었습니다.")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# -----------------------------
# 표준 공문형 인증서 설정
# -----------------------------
LineType = Union[str, Callable[[str, Dict[str, Any]], str]]

CERTIFICATE_CONFIG = {
    "allergen": {
        "subject": "알레르기 유발물질 함유 관련 件",
        "body_lines": [
            "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.",
            lambda product, row: f"2. 우리사에서 제조하는 {product} 제품은 알레르기 유발 물질을 함유하고 있지 않으며 교차오염 위험이",
            "   없음을 알려드립니다.",
        ],
        "table_headers": ["제품명", "알레르기 유발물질"],
        "table_values": lambda product, row: [product, "해당없음"],
    },
    "non_irradiated": {
        "subject": "방사선 조사 유무 관련 件",
        "body_lines": [
            "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.",
            lambda product, row: f"2. 우리사에서 제조하는 {product} 제품 생산시 원료의 구매, 제품 생산공정 및 보관, 운송되는 전 과정에서",
            "   방사선조사를 하지 않고 있음을 확인하여 드립니다.",
        ],
        "table_headers": ["제품명", "방사선조사 여부"],
        "table_values": lambda product, row: [product, "해당없음"],
    },
    "no_melamine": {
        "subject": "멜라민 미사용 확인",
        "body_lines": [
            "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.",
            lambda product, row: f"2. 우리사에서 제조하는 {product} 제품 제조공정 및 보관과정에서 멜라민을 사용하고 있지 않음을 확인하여",
            "   드립니다.",
        ],
        "table_headers": ["제품명", "멜라민 사용 여부"],
        "table_values": lambda product, row: [product, "해당없음"],
    },
    "gluten_free": {
        "subject": "글루텐 미함유 확인",
        "body_lines": [
            "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.",
            lambda product, row: f"2. 우리사에서 제조하는 {product} 제품에는 글루텐 유래 원료를 사용하지 않으며, 함유하고 있지 않습니다.",
        ],
        "table_headers": ["제품명", "글루텐 함유 여부"],
        "table_values": lambda product, row: [product, "미함유"],
    },
    "plant": {
        "subject": "식물성 원재료 사용 확인",
        "body_lines": [
            "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.",
            lambda product, row: f"2. 우리사에서 제조하는 {product} 제품은 자사 제조시설에서 식물성 원료인 옥수수만으로 제조되고 있으며",
            "   동물성 성분이 포함되지 않은 식물성 원료를 사용하였음을 확인하여 드립니다.",
        ],
        "table_headers": ["제품명", "식품성 원재료 사용 여부"],
        "table_values": lambda product, row: [product, "식물성 원재료 사용"],
    },
    "non_animal": {
        "subject": "비동물실험 확인",
        "body_lines": [
            "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.",
            lambda product, row: f"2. 우리사에서 제조하는 {product} 제품과 관련하여 개발부터 현재까지 동물실험을 하지 않았으며 향후에도",
            "   동물실험을 진행하지 않을 것임을 확인하여 드립니다.",
        ],
        "table_headers": ["제품명", "동물실험 여부"],
        "table_values": lambda product, row: [product, "해당없음"],
    },
    "no_pork": {
        "subject": "돼지고기 미사용 확인",
        "body_lines": [
            "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.",
            lambda product, row: f"2. 우리사에서 제조하는 {product} 제품은 돼지고기를 함유하지 있지 않으며, 제품을 생산하는 제조시설과",
            "   도구 또한 돼지고기와 돼지고기 유래 물질을 사용하지 않음을 확인하여 드립니다.",
        ],
        "table_headers": ["제품명", "돼지고기 사용 여부"],
        "table_values": lambda product, row: [product, "해당없음"],
    },
}


def resolve_line(line: LineType, product_name: str, row_data: Dict[str, Any]) -> str:
    if callable(line):
        return line(product_name, row_data)
    return str(line)


def generate_standard_certificate_pdf(
    product_name: str,
    cert_type: str,
    row_data: Dict[str, Any],
    receiver: str = "수신자제위",
) -> io.BytesIO:
    config = CERTIFICATE_CONFIG[cert_type]

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    today = datetime.today().strftime("%Y-%m-%d")

    draw_common_frame(c, width, height)
    info_top = draw_common_header(c, width, height)
    info_bottom = draw_info_box(
        c,
        width,
        info_top,
        today,
        receiver,
        config["subject"],
    )

    body_y = info_bottom - 35
    lines = [resolve_line(line, product_name, row_data) for line in config["body_lines"]]

    # 본문 출력
    current_y = body_y
    for i, line in enumerate(lines):
        x = 45 if i == 0 else 45
        if line.startswith("   "):
            x = 58
            line = line.strip()
        draw_text(c, x, current_y, line, 11, PDF_FONT)
        current_y -= 20 if i > 0 else 50

    # 표
    table_top = body_y - 85
    table_bottom = draw_two_column_table(
        c,
        width,
        table_top,
        headers=config["table_headers"],
        values=config["table_values"](product_name, row_data),
        left_ratio=0.4,
        x_margin=80,
        table_height=85,
    )

    draw_text(c, 45, table_bottom - 40, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.", 11, PDF_FONT)
    draw_text(c, width - 85, 160, "1부.끝.", 11, PDF_FONT)

    draw_common_footer(c, width)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# -----------------------------
# 원산지 증명 전용
# -----------------------------
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

    draw_common_frame(c, width, height)
    info_top = draw_common_header(c, width, height, company_name_spaced=True)
    info_bottom = draw_info_box(c, width, info_top, today, receiver, "원산지 증명")

    body_y = info_bottom - 35
    draw_text(c, 45, body_y, "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.", 11, PDF_FONT)
    draw_text(c, 45, body_y - 50, "2. 귀사에 납품되는 다음 제품의 원료 원산지는 아래와 같습니다.", 11, PDF_FONT)

    table_top = body_y - 85
    table_bottom = draw_three_column_table_for_origin(
        c,
        width,
        table_top,
        product_name=product_name,
        main_ingredient=main_ingredient,
        origin_country=origin_country,
        table_height=85,
    )

    draw_text(c, 45, table_bottom - 40, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.", 11, PDF_FONT)
    draw_text(c, width - 85, 120, "1부.끝.", 11, PDF_FONT)

    footer_y = 115
    draw_center(c, width / 2, footer_y, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(c, width / 2, footer_y - 22, "주식회사 삼양사", 12, PDF_FONT_BOLD)
    draw_center(c, width / 2, footer_y - 44, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 75, footer_y - 65, width=70, height=70, mask="auto")

    c.line(15, 35, width - 15, 35)
    draw_text(c, 32, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(c, width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(c, width - 160, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# -----------------------------
# 템플릿 타입별 PDF 생성기
# -----------------------------
STANDARD_CERT_TYPES = set(CERTIFICATE_CONFIG.keys())


def create_pdf_by_template_type(product_name: str, template_type: str, row_data: Dict[str, Any]) -> io.BytesIO:
    receiver = str(row_data.get("receiver", "수신자제위"))

    if template_type == "origin":
        return generate_origin_certificate_pdf(
            product_name=product_name,
            main_ingredient=str(row_data.get("main_ingredient", "-")),
            origin_country=str(row_data.get("origin_country", "-")),
            receiver=receiver,
        )
    elif template_type in STANDARD_CERT_TYPES:
        return generate_standard_certificate_pdf(
            product_name=product_name,
            cert_type=template_type,
            row_data=row_data,
            receiver=receiver,
        )
    else:
        return generate_template_pdf(product_name, template_type)


# -----------------------------
# 화면 표시 공통 함수
# -----------------------------
def render_document_row(
    product_code: str,
    idx: int,
    cert_name: str,
    file_bytes: bytes,
    output_file_name: str,
    doc_key_prefix: str,
):
    col1, col2, col3 = st.columns([0.5, 3.5, 1.0])

    with col1:
        checked = st.checkbox(
            label="",
            value=False,
            key=f"c_{doc_key_prefix}_{product_code}_{idx}",
            label_visibility="collapsed",
        )

    with col2:
        st.write(cert_name)

    with col3:
        st.download_button(
            label="다운로드",
            data=file_bytes,
            file_name=output_file_name,
            mime="application/pdf",
            key=f"d_{doc_key_prefix}_{product_code}_{idx}",
        )

    return checked


# -----------------------------
# 메인 화면
# -----------------------------
query_params = st.query_params
product_code = query_params.get("product")

if product_code:
    product_data = df[df["product_code"] == product_code].copy()

    if len(product_data) == 0:
        st.error("해당 제품을 찾을 수 없습니다.")
    else:
        product_data["has_content"] = product_data["file"].notna() | product_data["template_type"].notna()
        product_data = product_data.sort_values(by="has_content", ascending=False)
        product_data = product_data.drop_duplicates(subset=["cert_name"], keep="first")

        product_name = product_data.iloc[0]["product_name"]
        st.title(f"{product_name} 인증서 / 확인서")
        st.write("필요한 문서를 체크한 뒤 ZIP으로 한 번에 다운로드할 수 있습니다.")

        all_docs_for_zip = []

        for idx, row in product_data.reset_index(drop=True).iterrows():
            row_dict = row.to_dict()
            cert_name = str(row["cert_name"]).strip()
            doc_type = str(row["type"]).strip().lower()

            file_bytes = None
            output_file_name = None

            if doc_type == "file":
                file_name = str(row.get("file", "")).strip()

                if pd.isna(row.get("file")) or not file_name:
                    st.info(f"{cert_name}: 아직 등록되지 않았습니다.")
                    continue

                file_path = os.path.join(FILES_DIR, file_name)

                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()

                    output_file_name = file_name
                    checked = render_document_row(
                        product_code=product_code,
                        idx=idx,
                        cert_name=cert_name,
                        file_bytes=file_bytes,
                        output_file_name=output_file_name,
                        doc_key_prefix="file",
                    )
                    all_docs_for_zip.append((output_file_name, file_bytes, checked))
                else:
                    st.warning(f"{cert_name}: 파일 없음")

            elif doc_type == "template":
                template_type = str(row.get("template_type", "")).strip().lower()

                if not template_type or pd.isna(row.get("template_type")):
                    st.info(f"{cert_name}: 아직 등록되지 않았습니다.")
                    continue

                pdf_data = create_pdf_by_template_type(
                    product_name=product_name,
                    template_type=template_type,
                    row_data=row_dict,
                )

                file_bytes = pdf_data.getvalue()
                output_file_name = f"{product_name}_{cert_name}_{datetime.today().strftime('%Y%m%d')}.pdf"

                checked = render_document_row(
                    product_code=product_code,
                    idx=idx,
                    cert_name=cert_name,
                    file_bytes=file_bytes,
                    output_file_name=output_file_name,
                    doc_key_prefix="template",
                )
                all_docs_for_zip.append((output_file_name, file_bytes, checked))

            else:
                st.warning(f"{cert_name}: 지원하지 않는 문서 타입입니다. ({doc_type})")

        if all_docs_for_zip:
            st.divider()
            selected_docs = [(f, b) for f, b, c in all_docs_for_zip if c]
            if selected_docs:
                st.download_button(
                    label="선택한 문서 ZIP 다운로드",
                    data=build_zip_from_documents(selected_docs),
                    file_name=f"{product_name}_docs.zip",
                    mime="application/zip",
                )
            else:
                st.info("ZIP으로 받을 문서를 체크해주세요.")

else:
    st.title("제품별 인증서 / 확인서")
    products = df[["product_code", "product_name"]].drop_duplicates()
    for _, row in products.iterrows():
        st.markdown(f"- [{row['product_name']}](?product={row['product_code']})")
