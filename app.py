import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

st.set_page_config(page_title="인증서 다운로드", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "certificates.csv")
FILES_DIR = os.path.join(BASE_DIR, "files")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
STAMP_PATH = os.path.join(ASSETS_DIR, "stamp.png")

df = pd.read_csv(CSV_PATH)

# 한글 폰트 (assets 사용)
FONT_REGULAR_PATH = os.path.join(ASSETS_DIR, "NanumGothic.ttf")
FONT_BOLD_PATH = os.path.join(ASSETS_DIR, "NanumGothicBold.ttf")

pdfmetrics.registerFont(TTFont("Nanum", FONT_REGULAR_PATH))
pdfmetrics.registerFont(TTFont("Nanum-Bold", FONT_BOLD_PATH))

PDF_FONT = "Nanum"
PDF_FONT_BOLD = "Nanum-Bold"

def get_template_lines(product_name: str, template_type: str):
    if template_type == "origin":
        title = "원산지증명서"
        lines = [
            f"당사는 아래 제품의 원산지가 대한민국임을 확인합니다.",
            "",
            f"제품명: {product_name}",
            "원산지: 대한민국",
        ]

    elif template_type == "allergen":
        title = "알레르기유발물질 확인서"
        lines = [
            f"당사는 아래 제품에 대하여 원재료 및 제조공정 검토 결과를 바탕으로",
            "알레르기유발물질 관리사항을 확인하였음을 증명합니다.",
            "",
            f"제품명: {product_name}",
            "세부 사항은 당사 원재료 사양 및 제조공정 관리기준에 따릅니다.",
        ]

    elif template_type == "plant":
        title = "식물성 원재료 확인서"
        lines = [
            f"당사는 아래 제품의 원재료가 식물성 원재료 기준에 따라 검토되었음을 확인합니다.",
            "",
            f"제품명: {product_name}",
            "본 확인은 당사 원재료 구성 정보에 근거합니다.",
        ]

    elif template_type == "non_animal":
        title = "비동물성 원료 확인서"
        lines = [
            f"당사는 아래 제품이 동물성 유래 원료를 사용하지 않은 기준으로 검토되었음을 확인합니다.",
            "",
            f"제품명: {product_name}",
            "본 확인은 당사 원재료 구성 및 제조공정 정보에 근거합니다.",
        ]

    elif template_type == "no_pork":
        title = "돼지고기 미사용 확인서"
        lines = [
            f"당사는 아래 제품의 제조에 돼지고기 및 돼지고기 유래 원료를 사용하지 않음을 확인합니다.",
            "",
            f"제품명: {product_name}",
        ]

    elif template_type == "gluten_free":
        title = "글루텐 미함유 확인서"
        lines = [
            f"당사는 아래 제품에 대하여 원재료 및 제조공정 검토 결과를 바탕으로",
            "글루텐 미함유 기준에 따라 확인하였음을 증명합니다.",
            "",
            f"제품명: {product_name}",
        ]

    elif template_type == "non_irradiated":
        title = "방사선 비조사 확인서"
        lines = [
            f"당사는 아래 제품이 방사선 조사 처리되지 않았음을 확인합니다.",
            "",
            f"제품명: {product_name}",
        ]

    elif template_type == "no_melamine":
        title = "멜라민 미사용 확인서"
        lines = [
            f"당사는 아래 제품의 제조과정에서 멜라민을 사용하지 않음을 확인합니다.",
            "",
            f"제품명: {product_name}",
        ]

    else:
        title = "확인서"
        lines = [
            f"당사는 아래 제품에 대한 확인서를 발행합니다.",
            "",
            f"제품명: {product_name}",
        ]

    return title, lines


def generate_template_pdf(product_name: str, template_type: str) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    today = datetime.today().strftime("%Y-%m-%d")

    title, lines = get_template_lines(product_name, template_type)

    # 로고
    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 50, height - 90, width=140, height=40, mask='auto')

    # 제목
    c.setFont(PDF_FONT_BOLD, 18)
    c.drawCentredString(width / 2, height - 120, title)

    # 본문 시작
    y = height - 180
    line_gap = 24

    c.setFont(PDF_FONT, 11)
    for line in lines:
        if line == "":
            y -= 10
        else:
            c.drawString(70, y, line)
            y -= line_gap

    # 날짜 / 발행처
    y -= 20
    c.drawString(70, y, f"발행일자: {today}")
    y -= line_gap
    c.drawString(70, y, "발행처: 삼양사")
    y -= line_gap
    c.drawString(70, y, "발행부서: 품질 관련 부서")

    # 서명란
    y -= 60
    c.drawString(70, y, "상기와 같이 확인합니다.")

    y -= 50
    c.drawString(70, y, "삼양사")
    c.drawString(70, y - 22, "품질책임자: __________________")

    # 직인
    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, 220, y - 45, width=80, height=80, mask='auto')

    # 하단 문구
    c.setFont(PDF_FONT, 9)
    c.drawString(70, 50, "본 문서는 시스템에서 자동 생성되었습니다.")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def generate_origin_certificate_pdf(product_name: str,
                                    main_ingredient: str = "",
                                    origin_country: str = "") -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    today = datetime.today().strftime("%Y-%m-%d")

    def draw_text(x, y, text, size=11, font=PDF_FONT):
        c.setFont(font, size)
        c.drawString(x, y, text)

    def draw_center(x, y, text, size=11, font=PDF_FONT):
        c.setFont(font, size)
        c.drawCentredString(x, y, text)

    # 바깥 테두리
    c.rect(15, 15, width - 30, height - 30)

    # 로고
    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, 20, height - 55, width=110, height=25, mask='auto')

    # 회사명
    draw_center(width / 2, height - 38, "주식회사 삼 양 사", size=20, font=PDF_FONT_BOLD)

    # 상단 주소줄
    c.line(15, height - 68, width - 15, height - 68)
    draw_center(
        width / 2,
        height - 85,
        "우 22826 / 인천광역시 서구 백범로726 / 전화: 032)570-8229 / 팩스 : 032)570-8277",
        size=10
    )

    # 정보 박스
    info_top = height - 110
    info_bottom = height - 210
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    label_x = 30
    value_x = 110
    row_y = [info_top - 25, info_top - 55, info_top - 85, info_top - 115]

    draw_text(label_x, row_y[0], "발신일자 :", 12)
    draw_text(value_x, row_y[0], today, 12)

    draw_text(label_x, row_y[1], "수    신 :", 12)
    draw_text(value_x, row_y[1], "수신자제위", 12)

    draw_text(label_x, row_y[2], "참    조 :", 12)

    draw_text(label_x, row_y[3], "제    목 :", 12)
    draw_text(value_x, row_y[3], "원산지 증명", 12)

    # 본문
    body_y = info_bottom - 35
    draw_text(
        40, body_y,
        "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어",
        11
    )
    draw_text(
        60, body_y - 22,
        "주신 각별한 애호에 감사 드립니다.",
        11
    )

    draw_text(
        40, body_y - 65,
        "2. 귀사에 납품되는 다음 제품의 원료 원산지는 아래와 같습니다.",
        11
    )

    # 표
    table_top = body_y - 95
    table_bottom = table_top - 75

    x0 = 25
    x1 = 170
    x2 = 340
    x3 = width - 25

    c.rect(x0, table_bottom, x3 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)
    c.line(x2, table_bottom, x2, table_top)

    header_y = table_top - 25
    c.line(x0, header_y, x3, header_y)

    draw_center((x0 + x1) / 2, table_top - 17, "제품명", 11, PDF_FONT_BOLD)
    draw_center((x1 + x2) / 2, table_top - 17, "주원료", 11, PDF_FONT_BOLD)
    draw_center((x2 + x3) / 2, table_top - 17, "원료원산지", 11, PDF_FONT_BOLD)

    draw_center((x0 + x1) / 2, table_bottom + 22, product_name, 16)
    draw_center((x1 + x2) / 2, table_bottom + 22, main_ingredient or "-", 13)
    draw_center((x2 + x3) / 2, table_bottom + 22, origin_country or "-", 13)

    # 3항
    draw_text(
        40, table_bottom - 40,
        "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.",
        11
    )

    # 우측 하단
    draw_text(width - 95, 120, "1부.끝.", 11)

    # 하단 주소 / 회사명 / 팀장
    draw_center(width / 2, 85, "인천광역시 서구 백범로 726", 11)
    draw_center(width / 2, 63, "주식회사 삼양사", 11)
    draw_center(width / 2, 41, "식품안전팀장", 11)

    # 직인
    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 120, 28, width=70, height=70, mask='auto')

    # 하단 서식 문구
    c.line(15, 35, width - 15, 35)
    draw_text(35, 22, "서식3-J113Rev.0", 9)
    draw_center(width / 2, 22, "㈜삼양사 인천1공장", 9)
    draw_text(width - 170, 22, "A4(210mm X 297mm)", 9)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


query_params = st.query_params
product_code = query_params.get("product")

if product_code:
    product_data = df[df["product_code"] == product_code]

    if len(product_data) == 0:
        st.error("해당 제품을 찾을 수 없습니다.")
    else:
        product_name = product_data.iloc[0]["product_name"]
        st.title(f"{product_name} 인증서 / 확인서")

        for idx, row in product_data.reset_index(drop=True).iterrows():
            cert_name = str(row["cert_name"])
            doc_type = str(row["type"]).strip().lower()
            safe_cert_name = cert_name.strip().replace(" ", "_")

            if doc_type == "file":
                file_name = row["file"]

                if pd.isna(file_name) or str(file_name).strip() == "":
                    st.warning(f"{cert_name}: 파일명이 비어 있습니다.")
                    continue

                file_name = str(file_name).strip()
                file_path = os.path.join(FILES_DIR, file_name)

                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"{cert_name} 다운로드",
                            data=f,
                            file_name=file_name,
                            mime="application/pdf",
                            key=f"file_{product_code}_{safe_cert_name}_{idx}"
                        )
                else:
                    st.warning(f"{cert_name}: 파일 없음 ({file_name})")

            elif doc_type == "template":
                template_type = ""
                if "template_type" in row.index and not pd.isna(row["template_type"]):
                    template_type = str(row["template_type"]).strip().lower()

                if template_type == "":
                    st.warning(f"{cert_name}: template_type이 비어 있습니다.")
                    continue

                if template_type == "origin":
                    main_ingredient = ""
                    origin_country = ""

                    if "main_ingredient" in row.index and not pd.isna(row["main_ingredient"]):
                        main_ingredient = str(row["main_ingredient"]).strip()

                    if "origin_country" in row.index and not pd.isna(row["origin_country"]):
                        origin_country = str(row["origin_country"]).strip()

                    pdf_data = generate_origin_certificate_pdf(
                        product_name=product_name,
                        main_ingredient=main_ingredient,
                        origin_country=origin_country
                    )
                else:
                    pdf_data = generate_template_pdf(product_name, template_type)

                st.download_button(
                    label=f"{cert_name} 발급",
                    data=pdf_data,
                    file_name=f"{product_name}_{cert_name}_{datetime.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key=f"template_{product_code}_{safe_cert_name}_{template_type}_{idx}"
                )

            else:
                st.warning(f"{cert_name}: type 값이 올바르지 않습니다.")

else:
    st.title("제품별 인증서 / 확인서")
    st.write("제품을 선택하세요.")

    products = df[["product_code", "product_name"]].drop_duplicates()

    for _, row in products.iterrows():
        st.markdown(f"- [{row['product_name']}](?product={row['product_code']})")
