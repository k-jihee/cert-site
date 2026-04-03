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

# 한글 폰트
FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("Malgun", FONT_PATH))
    PDF_FONT = "Malgun"
else:
    PDF_FONT = "Helvetica"


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
    c.setFont(PDF_FONT, 18)
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
                if not pd.isna(row["template_type"]):
                    template_type = str(row["template_type"]).strip()

                if template_type == "":
                    st.warning(f"{cert_name}: template_type이 비어 있습니다.")
                    continue

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