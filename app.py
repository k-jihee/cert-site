import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

st.set_page_config(page_title="인증서 다운로드", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "certificates.csv")
FILES_DIR = os.path.join(BASE_DIR, "files")

df = pd.read_csv(CSV_PATH)

# 한글 폰트 등록
FONT_PATH = "C:/Windows/Fonts/malgun.ttf"
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("Malgun", FONT_PATH))
    PDF_FONT = "Malgun"
else:
    PDF_FONT = "Helvetica"


def generate_template_pdf(product_name: str, cert_name: str, template_type: str) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    today = datetime.today().strftime("%Y-%m-%d")

    c.setFont(PDF_FONT, 18)
    c.drawCentredString(width / 2, height - 80, cert_name)

    c.setFont(PDF_FONT, 11)
    y = height - 140
    line_gap = 24

    c.drawString(70, y, f"제품명: {product_name}")
    y -= line_gap
    c.drawString(70, y, f"발행일자: {today}")
    y -= line_gap * 2

    if template_type == "origin":
        lines = [
            f"당사는 상기 제품의 원산지가 대한민국임을 확인합니다.",
        ]
    elif template_type == "allergen":
        lines = [
            f"당사는 상기 제품에 대해 알레르기 유발물질 관리 기준에 따라 검토하였음을 확인합니다.",
            f"세부 내용은 내부 기준 및 원재료 정보를 기반으로 작성되었습니다.",
        ]
    elif template_type == "plant":
        lines = [
            f"당사는 상기 제품이 식물성 원재료 기준에 따라 검토되었음을 확인합니다.",
        ]
    elif template_type == "non_animal":
        lines = [
            f"당사는 상기 제품이 비동물성 원료 기준에 따라 검토되었음을 확인합니다.",
        ]
    elif template_type == "no_pork":
        lines = [
            f"당사는 상기 제품의 제조 시 돼지고기 유래 원료를 사용하지 않음을 확인합니다.",
        ]
    elif template_type == "gluten_free":
        lines = [
            f"당사는 상기 제품이 글루텐 미함유 기준에 따라 검토되었음을 확인합니다.",
        ]
    elif template_type == "non_irradiated":
        lines = [
            f"당사는 상기 제품이 방사선 조사 처리되지 않았음을 확인합니다.",
        ]
    elif template_type == "no_melamine":
        lines = [
            f"당사는 상기 제품의 제조 과정에서 멜라민을 사용하지 않음을 확인합니다.",
        ]
    else:
        lines = [
            f"당사는 상기 제품에 대한 확인서를 발행합니다.",
        ]

    for line in lines:
        c.drawString(70, y, line)
        y -= line_gap

    y -= line_gap * 2
    c.drawString(70, y, "발행처: 삼양사")
    y -= line_gap
    c.drawString(70, y, "담당부서: 품질 관련 부서")
    y -= line_gap
    c.drawString(70, y, "본 문서는 시스템에서 자동 생성되었습니다.")

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

        for _, row in product_data.iterrows():
            cert_name = str(row["cert_name"])
            doc_type = str(row["type"]).strip().lower()

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
                            key=f"file_{product_code}_{cert_name}"
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

                pdf_data = generate_template_pdf(product_name, cert_name, template_type)

                st.download_button(
                    label=f"{cert_name} 발급",
                    data=pdf_data,
                    file_name=f"{product_name}_{cert_name}_{datetime.today().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key=f"template_{product_code}_{cert_name}"
                )

            else:
                st.warning(f"{cert_name}: type 값이 올바르지 않습니다. (file 또는 template)")

else:
    st.title("제품별 인증서 / 확인서")
    st.write("제품을 선택하세요.")

    products = df[["product_code", "product_name"]].drop_duplicates()

    for _, row in products.iterrows():
        st.markdown(f"- [{row['product_name']}](?product={row['product_code']})")
