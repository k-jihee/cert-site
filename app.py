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

# 동일 문서 중복 제거 (기본)
dedupe_cols = ["product_code", "cert_name", "type", "template_type", "file"]
existing_dedupe_cols = [col for col in dedupe_cols if col in df.columns]
if existing_dedupe_cols:
    df = df.drop_duplicates(subset=existing_dedupe_cols, keep="first")


def get_template_lines(product_name: str, template_type: str):
    if template_type == "plant":
        title = "식물성 원재료 확인서"
        lines = [
            "당사는 아래 제품의 원재료가 식물성 원재료 기준에 따라 검토되었음을 확인합니다.",
            "",
            f"제품명: {product_name}",
            "본 확인은 당사 원재료 구성 정보에 근거합니다.",
        ]
    elif template_type == "non_animal":
        title = "비동물성 원료 확인서"
        lines = [
            "당사는 아래 제품이 동물성 유래 원료를 사용하지 않은 기준으로 검토되었음을 확인합니다.",
            "",
            f"제품명: {product_name}",
            "본 확인은 당사 원재료 구성 및 제조공정 정보에 근거합니다.",
        ]
    elif template_type == "no_pork":
        title = "돼지고기 미사용 확인서"
        lines = [
            "당사는 아래 제품의 제조에 돼지고기 및 돼지고기 유래 원료를 사용하지 않음을 확인합니다.",
            "",
            f"제품명: {product_name}",
        ]
    elif template_type == "gluten_free":
        title = "글루텐 미함유 확인서"
        lines = [
            "당사는 아래 제품에 대하여 원재료 및 제조공정 검토 결과를 바탕으로",
            "글루텐 미함유 기준에 따라 확인하였음을 증명합니다.",
            "",
            f"제품명: {product_name}",
        ]
    elif template_type == "no_melamine":
        title = "멜라민 미사용 확인서"
        lines = [
            "당사는 아래 제품의 제조과정에서 멜라민을 사용하지 않음을 확인합니다.",
            "",
            f"제품명: {product_name}",
        ]
    else:
        title = "확인서"
        lines = [
            "당사는 아래 제품에 대한 확인서를 발행합니다.",
            "",
            f"제품명: {product_name}",
        ]

    return title, lines


def draw_wrapped_centered_text(c, text, center_x, start_y, max_width, font_name, font_size, line_gap=14):
    """텍스트를 줄바꿈하여 지정된 x축 중앙에 맞춰 그리는 함수"""
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

    # 전체 텍스트 높이를 고려하여 시작 Y 위치 보정 (수직 중앙 정렬용)
    total_height = (len(lines) - 1) * line_gap
    y_offset = start_y + (total_height / 2)

    for i, line in enumerate(lines):
        c.drawCentredString(center_x, y_offset - (i * line_gap), line)


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

    #외곽 테두리
    c.setLineWidth(0.8)
    c.rect(15, 15, width - 30, height - 30)

    # 상단 헤더 영역(로고 및 회사명)
    header_top = height - 15
    header_line = height - 70
    
    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 30, height - 55, width=110, height=24, mask="auto")

    # 회사명 상하중앙 정렬(15~70 사이 정중앙)
    draw_center(width / 2, (header_top + header_line)/2 - 8, "주식회사 삼 양 사", size=22, font=PDF_FONT_BOLD)
    c.line(15, header_line, width - 15, header_line)

    # 주소 영역 상하중앙 정렬
    address_line = height - 95
    draw_center(width / 2, (header_line + address_line)/2 - 3,
                "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277",
                size=9.5, font=PDF_FONT)
    c.line(15, address_line, width - 15, address_line)

    # 정보 박스(발신일자, 수신등)
    info_top = address_line
    info_height = 110
    info_bottom = info_top - info_height
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    row_gap = 26
    font_size = 11
    num_rows = 4

    text_block_height = font_size + row_gap * (num_rows - 1)
    top_bottom_padding = (info_height - text_block_height) / 2
    start_y = info_top - top_bottom_padding - font_size + 2
    
    draw_text(35, start_y, "발신일자 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y, today, font_size, PDF_FONT)
    
    draw_text(35, start_y - row_gap, "수    신 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap, receiver or "수신자제위", font_size, PDF_FONT)

    draw_text(35, start_y - row_gap*2, "참    조 :", font_size, PDF_FONT_BOLD)

    # 제목 위치 조정 (선이 글자 아래로 가도록)
    draw_text(35, start_y - row_gap*3, "제    목 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap*3, "원산지 증명", font_size, PDF_FONT) 

    body_y = info_bottom - 35
    draw_text(45, body_y, "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.", 11, PDF_FONT)
    draw_text(45, body_y - 50, "2. 귀사에 납품되는 다음 제품의 원료 원산지는 아래와 같습니다.", 11, PDF_FONT)

    # 제품 정보 테이블 설정
    table_top = body_y - 85
    table_height = 85   
    table_bottom = table_top - table_height
    x0, x1, x2, x3 = 25, 170, 340, width - 25

    c.rect(x0, table_bottom, x3 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)
    c.line(x2, table_bottom, x2, table_top)

    header_h = 28
    c.line(x0, table_top - header_h, x3, table_top - header_h)

    # 헤더 텍스트
    draw_center((x0 + x1) / 2, table_top - 15, "제품명", 12, PDF_FONT_BOLD)
    draw_center((x1 + x2) / 2, table_top - 15, "주원료", 12, PDF_FONT_BOLD)
    draw_center((x2 + x3) / 2, table_top - 15, "원료원산지", 12, PDF_FONT_BOLD)

    content_mid_y = table_bottom + (table_height - header_h) / 2 - 4
    draw_center((x0 + x1) / 2, content_mid_y, product_name, 12, PDF_FONT)
    draw_center((x1 + x2) / 2, content_mid_y, main_ingredient or "-", 11, PDF_FONT)

    draw_wrapped_centered_text(c, origin_country or "-", (x2 + x3) / 2, content_mid_y + 2, 
                               (x3 - x2) - 15, PDF_FONT, 10, line_gap=13)

    draw_text(45, table_bottom - 40, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.", 11, PDF_FONT)
    draw_text(width - 85, 120, "1부.끝.", 11, PDF_FONT)

    # 하단 직인 및 주소 영역
    footer_y = 115
    draw_center(width / 2, footer_y, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(width / 2, footer_y - 22, "주식회사 삼양사", 12, PDF_FONT_BOLD)
    draw_center(width / 2, footer_y - 44, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 75, footer_y - 65, width=70, height=70, mask="auto")

    c.line(15, 35, width - 15, 35)
    draw_text(32, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(width - 160, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def generate_allergen_certificate_pdf(
    product_name: str,
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

    # 상단 헤더 영역
    header_top = height - 15
    header_line = height - 70

    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 30, height - 55, width=110, height=24, mask="auto")

    draw_center(width / 2, (header_top + header_line)/2 - 8, "주식회사 삼양사", size=22, font=PDF_FONT_BOLD)
    c.line(15, header_line, width - 15, header_line)

    # 주소 영역
    address_line = height - 95
    draw_center(
        width / 2,
        (header_line + address_line)/2 - 3,
        "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277",
        size=9.5,
        font=PDF_FONT
    )
    c.line(15, address_line, width - 15, address_line)

    # 정보 박스
    info_top = address_line
    info_height = 110
    info_bottom = info_top - info_height
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    row_gap = 26
    font_size = 11
    num_rows = 4

    text_block_height = font_size + row_gap * (num_rows - 1)
    top_bottom_padding = (info_height - text_block_height) / 2
    start_y = info_top - top_bottom_padding - font_size + 2

    draw_text(35, start_y, "발신일자 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y, today, font_size, PDF_FONT)

    draw_text(35, start_y - row_gap, "수    신 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap, receiver or "수신자제위", font_size, PDF_FONT)

    draw_text(35, start_y - row_gap*2, "참    조 :", font_size, PDF_FONT_BOLD)

    draw_text(35, start_y - row_gap*3, "제    목 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap*3, "알레르기 유발물질 함유 관련 件", font_size, PDF_FONT)

    body_y = info_bottom - 35
    draw_text(45, body_y, "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.", 11, PDF_FONT)
    draw_text(45, body_y - 50, f"2. 우리사에서 제조하는 {product_name} 제품은 알레르기 유발 물질을 함유하고 있지 않으며 교차오염 위험이", 11, PDF_FONT)
    draw_text(58, body_y - 70, "없음을 알려드립니다.", 11,PDF_FONT)

    # 표 
    table_top = body_y - 85
    table_height = 85
    table_bottom = table_top - table_height

    x0 = 80
    x2 = width - 80
    x1 = x0 + (x2 - x0) * 0.4   # 왼쪽 40%, 오른쪽 60% 비율

    c.rect(x0, table_bottom, x2 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)

    header_h = 28
    c.line(x0, table_top - header_h, x2, table_top - header_h)

    draw_center((x0 + x1) / 2, table_top - 15, "제품명", 12, PDF_FONT_BOLD)
    draw_center((x1 + x2) / 2, table_top - 15, "알레르기 유발물질", 12, PDF_FONT_BOLD)

    content_mid_y = table_bottom + (table_height - header_h) / 2 - 4
    draw_center((x0 + x1) / 2, content_mid_y, product_name, 12, PDF_FONT)
    draw_center((x1 + x2) / 2, content_mid_y, "해당없음", 11, PDF_FONT)
    
    draw_text(45, table_bottom - 40, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.", 11, PDF_FONT)
    draw_text(width - 85, 120, "1부.끝.", 11, PDF_FONT)

    footer_y = 115
    draw_center(width / 2, footer_y, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(width / 2, footer_y - 22, "주식회사 삼양사", 12, PDF_FONT_BOLD)
    draw_center(width / 2, footer_y - 44, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 75, footer_y - 65, width=70, height=70, mask="auto")

    c.line(15, 35, width - 15, 35)
    draw_text(32, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(width - 160, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def generate_non_irradiated_certificate_pdf(
    product_name: str,
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

    # 상단 헤더 영역
    header_top = height - 15
    header_line = height - 70

    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 30, height - 55, width=110, height=24, mask="auto")

    draw_center(width / 2, (header_top + header_line)/2 - 8, "주식회사 삼양사", size=22, font=PDF_FONT_BOLD)
    c.line(15, header_line, width - 15, header_line)

    # 주소 영역
    address_line = height - 95
    draw_center(
        width / 2,
        (header_line + address_line)/2 - 3,
        "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277",
        size=9.5,
        font=PDF_FONT
    )
    c.line(15, address_line, width - 15, address_line)

    # 정보 박스
    info_top = address_line
    info_height = 110
    info_bottom = info_top - info_height
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    row_gap = 26
    font_size = 11
    num_rows = 4

    text_block_height = font_size + row_gap * (num_rows - 1)
    top_bottom_padding = (info_height - text_block_height) / 2
    start_y = info_top - top_bottom_padding - font_size + 2

    draw_text(35, start_y, "발신일자 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y, today, font_size, PDF_FONT)

    draw_text(35, start_y - row_gap, "수    신 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap, receiver or "수신자제위", font_size, PDF_FONT)

    draw_text(35, start_y - row_gap*2, "참    조 :", font_size, PDF_FONT_BOLD)

    draw_text(35, start_y - row_gap*3, "제    목 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap*3, "방사선 조사 유무 관련 件", font_size, PDF_FONT)

    body_y = info_bottom - 35
    draw_text(45, body_y, "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.", 11, PDF_FONT)
    draw_text(45, body_y - 50, f"2. 우리사에서 제조하는 {product_name} 제품 생산시 원료의 구매, 제품 생산공정 및 보관, 운송되는 전 과정에서", 11, PDF_FONT)
    draw_text(58, body_y - 70, "방사선조사를 하지 않고 있음을 확인하여 드립니다.", 11,PDF_FONT)

    # 표 
    table_top = body_y - 85
    table_height = 85
    table_bottom = table_top - table_height

    x0 = 80
    x2 = width - 80
    x1 = x0 + (x2 - x0) * 0.4   # 왼쪽 40%, 오른쪽 60% 비율

    c.rect(x0, table_bottom, x2 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)

    header_h = 28
    c.line(x0, table_top - header_h, x2, table_top - header_h)

    draw_center((x0 + x1) / 2, table_top - 15, "제품명", 12, PDF_FONT_BOLD)
    draw_center((x1 + x2) / 2, table_top - 15, "방사선조사 여부", 12, PDF_FONT_BOLD)

    content_mid_y = table_bottom + (table_height - header_h) / 2 - 4
    draw_center((x0 + x1) / 2, content_mid_y, product_name, 12, PDF_FONT)
    draw_center((x1 + x2) / 2, content_mid_y, "해당없음", 11, PDF_FONT)
    
    draw_text(45, table_bottom - 40, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.", 11, PDF_FONT)
    draw_text(width - 85, 120, "1부.끝.", 11, PDF_FONT)

    footer_y = 115
    draw_center(width / 2, footer_y, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(width / 2, footer_y - 22, "주식회사 삼양사", 12, PDF_FONT_BOLD)
    draw_center(width / 2, footer_y - 44, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 75, footer_y - 65, width=70, height=70, mask="auto")

    c.line(15, 35, width - 15, 35)
    draw_text(32, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(width - 160, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def generate_no_melamine_certificate_pdf(
    product_name: str,
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

    # 상단 헤더 영역
    header_top = height - 15
    header_line = height - 70

    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 30, height - 55, width=110, height=24, mask="auto")

    draw_center(width / 2, (header_top + header_line)/2 - 8, "주식회사 삼양사", size=22, font=PDF_FONT_BOLD)
    c.line(15, header_line, width - 15, header_line)

    # 주소 영역
    address_line = height - 95
    draw_center(
        width / 2,
        (header_line + address_line)/2 - 3,
        "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277",
        size=9.5,
        font=PDF_FONT
    )
    c.line(15, address_line, width - 15, address_line)

    # 정보 박스
    info_top = address_line
    info_height = 110
    info_bottom = info_top - info_height
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    row_gap = 26
    font_size = 11
    num_rows = 4

    text_block_height = font_size + row_gap * (num_rows - 1)
    top_bottom_padding = (info_height - text_block_height) / 2
    start_y = info_top - top_bottom_padding - font_size + 2

    draw_text(35, start_y, "발신일자 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y, today, font_size, PDF_FONT)

    draw_text(35, start_y - row_gap, "수    신 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap, receiver or "수신자제위", font_size, PDF_FONT)

    draw_text(35, start_y - row_gap*2, "참    조 :", font_size, PDF_FONT_BOLD)

    draw_text(35, start_y - row_gap*3, "제    목 :", font_size, PDF_FONT_BOLD)
    draw_text(100, start_y - row_gap*3, "멜라민 미사용 확인", font_size, PDF_FONT)

    body_y = info_bottom - 35
    draw_text(45, body_y, "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어 주신 각별한 애호에 감사드립니다.", 11, PDF_FONT)
    draw_text(45, body_y - 50, f"2. 우리사에서 제조하는 {product_name} 제품 제조공정 및 보관과정에서 멜라민을 사용하고 있지 않음을 확인하여 드립니다., 11, PDF_FONT)
    
    # 표 
    table_top = body_y - 85
    table_height = 85
    table_bottom = table_top - table_height

    x0 = 80
    x2 = width - 80
    x1 = x0 + (x2 - x0) * 0.4   # 왼쪽 40%, 오른쪽 60% 비율

    c.rect(x0, table_bottom, x2 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)

    header_h = 28
    c.line(x0, table_top - header_h, x2, table_top - header_h)

    draw_center((x0 + x1) / 2, table_top - 15, "제품명", 12, PDF_FONT_BOLD)
    draw_center((x1 + x2) / 2, table_top - 15, "멜라민 사용 여부", 12, PDF_FONT_BOLD)

    content_mid_y = table_bottom + (table_height - header_h) / 2 - 4
    draw_center((x0 + x1) / 2, content_mid_y, product_name, 12, PDF_FONT)
    draw_center((x1 + x2) / 2, content_mid_y, "해당없음", 11, PDF_FONT)
    
    draw_text(45, table_bottom - 40, "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.", 11, PDF_FONT)
    draw_text(width - 85, 120, "1부.끝.", 11, PDF_FONT)

    footer_y = 115
    draw_center(width / 2, footer_y, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(width / 2, footer_y - 22, "주식회사 삼양사", 12, PDF_FONT_BOLD)
    draw_center(width / 2, footer_y - 44, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 75, footer_y - 65, width=70, height=70, mask="auto")

    c.line(15, 35, width - 15, 35)
    draw_text(32, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(width - 160, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def build_zip_from_documents(documents: List[Tuple[str, bytes]]) -> io.BytesIO:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name, file_bytes in documents:
            zip_file.writestr(file_name, file_bytes)
    zip_buffer.seek(0)
    return zip_buffer

query_params = st.query_params
product_code = query_params.get("product")

if product_code:
    product_data = df[df["product_code"] == product_code].copy()

    if len(product_data) == 0:
        st.error("해당 제품을 찾을 수 없습니다.")
    else:
        # 중복 방지: 내용이 있는 행 우선 정렬 후 이름 기준 중복 제거
        product_data['has_content'] = product_data['file'].notna() | product_data['template_type'].notna()
        product_data = product_data.sort_values(by='has_content', ascending=False)
        product_data = product_data.drop_duplicates(subset=['cert_name'], keep='first')

        product_name = product_data.iloc[0]["product_name"]
        st.title(f"{product_name} 인증서 / 확인서")
        st.write("필요한 문서를 체크한 뒤 ZIP으로 한 번에 다운로드할 수 있습니다.")

        all_docs_for_zip = []

        for idx, row in product_data.reset_index(drop=True).iterrows():
            cert_name = str(row["cert_name"])
            doc_type = str(row["type"]).strip().lower()
            safe_cert_name = cert_name.strip().replace(" ", "_")
            file_bytes, output_file_name = None, None

            # 레이아웃 간격 고정
            col1, col2, col3 = st.columns([0.5, 3.5, 1.0])

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

                    with col1:
                        checked = st.checkbox(label="", value=False, key=f"c_f_{product_code}_{idx}", label_visibility="collapsed")
                    with col2:
                        st.write(cert_name)
                    with col3:
                        st.download_button(label="다운로드", data=file_bytes, file_name=output_file_name, mime="application/pdf", key=f"f_{product_code}_{idx}")
                    all_docs_for_zip.append((output_file_name, file_bytes, checked))
                else:
                    st.warning(f"{cert_name}: 파일 없음")

            elif doc_type == "template":
                template_type = str(row.get("template_type", "")).strip().lower()
                if not template_type or pd.isna(row.get("template_type")):
                    st.info(f"{cert_name}: 아직 등록되지 않았습니다.")
                    continue

                if template_type == "origin":
                    pdf_data = generate_origin_certificate_pdf(
                        product_name=product_name,
                        main_ingredient=str(row.get("main_ingredient", "-")),
                        origin_country=str(row.get("origin_country", "-")),
                        receiver=str(row.get("receiver", "수신자제위"))
                    )
                elif template_type == "allergen":
                    pdf_data = generate_allergen_certificate_pdf(
                        product_name=product_name,
                        receiver=str(row.get("receiver", "수신자제위"))
                    )
                elif template_type == "non_irradiated":
                    pdf_data = generate_non_irradiated_certificate_pdf(
                        product_name=product_name,
                        receiver=str(row.get("receiver", "수신자제위"))
                    )
                elif template_type == "no_melamine":
                    pdf_data = generate_non_irradiated_certificate_pdf(
                        product_name=product_name,
                        receiver=str(row.get("receiver", "수신자제위"))
                    )
                else:
                    pdf_data = generate_template_pdf(product_name, template_type)

                file_bytes = pdf_data.getvalue()
                output_file_name = f"{product_name}_{cert_name}_{datetime.today().strftime('%Y%m%d')}.pdf"

                with col1:
                    checked = st.checkbox(label="", value=False, key=f"c_t_{product_code}_{idx}", label_visibility="collapsed")
                with col2:
                    st.write(cert_name)
                with col3:
                    st.download_button(label="다운로드", data=file_bytes, file_name=output_file_name, mime="application/pdf", key=f"t_{product_code}_{idx}")
                all_docs_for_zip.append((output_file_name, file_bytes, checked))

        if all_docs_for_zip:
            st.divider()
            selected_docs = [(f, b) for f, b, c in all_docs_for_zip if c]
            if selected_docs:
                st.download_button(label="선택한 문서 ZIP 다운로드", data=build_zip_from_documents(selected_docs), file_name=f"{product_name}_docs.zip", mime="application/zip")
            else:
                st.info("ZIP으로 받을 문서를 체크해주세요.")
else:
    st.title("제품별 인증서 / 확인서")
    products = df[["product_code", "product_name"]].drop_duplicates()
    for _, row in products.iterrows():
        st.markdown(f"- [{row['product_name']}](?product={row['product_code']})")
