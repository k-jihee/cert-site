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


def get_template_lines(product_name: str, template_type: str):
    if template_type == "allergen":
        title = "알레르기유발물질 확인서"
        lines = [
            "당사는 아래 제품에 대하여 원재료 및 제조공정 검토 결과를 바탕으로",
            "알레르기유발물질 관리사항을 확인하였음을 증명합니다.",
            "",
            f"제품명: {product_name}",
            "세부 사항은 당사 원재료 사양 및 제조공정 관리기준에 따릅니다.",
        ]
    elif template_type == "plant":
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
    elif template_type == "non_irradiated":
        title = "방사선 비조사 확인서"
        lines = [
            "당사는 아래 제품이 방사선 조사 처리되지 않았음을 확인합니다.",
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


def draw_wrapped_text(c, text, x, y, max_width, font_name, font_size, line_gap=14):
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

    for i, line in enumerate(lines):
        c.drawString(x, y - i * line_gap, line)

    return y - (len(lines) - 1) * line_gap


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

    page_left = 28

    def draw_text(x, y, text, size=11, font=PDF_FONT):
        c.setFont(font, size)
        c.drawString(x, y, str(text))

    def draw_center(x, y, text, size=11, font=PDF_FONT):
        c.setFont(font, size)
        c.drawCentredString(x, y, str(text))

    c.setLineWidth(0.8)
    c.rect(15, 15, width - 30, height - 30)

    if os.path.exists(LOGO_PATH):
        logo = ImageReader(LOGO_PATH)
        c.drawImage(logo, page_left, height - 52, width=110, height=24, mask="auto")

    draw_center(width / 2, height - 38, "주식회사 삼 양 사", size=21, font=PDF_FONT_BOLD)

    c.line(15, height - 66, width - 15, height - 66)
    draw_center(
        width / 2,
        height - 83,
        "우 22826 / 인천광역시 서구 백범로 726 / 전화: 032)570-8229 / 팩스: 032)570-8277",
        size=9.5,
        font=PDF_FONT,
    )

    info_top = height - 108
    info_bottom = height - 210
    c.rect(15, info_bottom, width - 30, info_top - info_bottom)

    row_1 = info_top - 24
    row_2 = info_top - 52
    row_3 = info_top - 80
    row_4 = info_top - 108

    label_x = 30
    value_x = 110

    draw_text(label_x, row_1, "발신일자 :", 11, PDF_FONT_BOLD)
    draw_text(value_x, row_1, today, 11, PDF_FONT)

    draw_text(label_x, row_2, "수    신 :", 11, PDF_FONT_BOLD)
    draw_text(value_x, row_2, receiver or "수신자제위", 11, PDF_FONT)

    draw_text(label_x, row_3, "참    조 :", 11, PDF_FONT_BOLD)

    draw_text(label_x, row_4, "제    목 :", 11, PDF_FONT_BOLD)
    draw_text(value_x, row_4, "원산지 증명", 11, PDF_FONT)

    body_y = info_bottom - 30
    draw_text(
        40,
        body_y,
        "1. 귀사의 일익 번창하심을 진심으로 기원하오며, 그 동안 저희 사에 베풀어",
        11,
        PDF_FONT,
    )
    draw_text(
        58,
        body_y - 20,
        "주신 각별한 애호에 감사 드립니다.",
        11,
        PDF_FONT,
    )

    draw_text(
        40,
        body_y - 58,
        "2. 귀사에 납품되는 다음 제품의 원료 원산지는 아래와 같습니다.",
        11,
        PDF_FONT,
    )

    table_top = body_y - 88
    table_bottom = table_top - 74

    x0 = 25
    x1 = 170
    x2 = 340
    x3 = width - 25

    c.rect(x0, table_bottom, x3 - x0, table_top - table_bottom)
    c.line(x1, table_bottom, x1, table_top)
    c.line(x2, table_bottom, x2, table_top)

    header_y = table_top - 24
    c.line(x0, header_y, x3, header_y)

    draw_center((x0 + x1) / 2, table_top - 16, "제품명", 10.5, PDF_FONT_BOLD)
    draw_center((x1 + x2) / 2, table_top - 16, "주원료", 10.5, PDF_FONT_BOLD)
    draw_center((x2 + x3) / 2, table_top - 16, "원료원산지", 10.5, PDF_FONT_BOLD)

    draw_center((x0 + x1) / 2, table_bottom + 22, product_name, 14, PDF_FONT)
    draw_center((x1 + x2) / 2, table_bottom + 22, main_ingredient or "-", 12, PDF_FONT)

    draw_wrapped_text(
        c,
        origin_country or "-",
        x2 + 8,
        table_bottom + 30,
        (x3 - x2) - 16,
        PDF_FONT,
        10.5,
        line_gap=12,
    )

    draw_text(
        40,
        table_bottom - 34,
        "3. 향후에도 양질의 제품만을 공급해 드릴 수 있도록 최선을 다하겠습니다.",
        11,
        PDF_FONT,
    )

    draw_text(width - 82, 118, "1부.끝.", 10.5, PDF_FONT)

    draw_center(width / 2, 86, "인천광역시 서구 백범로 726", 11, PDF_FONT)
    draw_center(width / 2, 64, "주식회사 삼양사", 11, PDF_FONT)
    draw_center(width / 2, 42, "식품안전팀장", 11, PDF_FONT)

    if os.path.exists(STAMP_PATH):
        stamp = ImageReader(STAMP_PATH)
        c.drawImage(stamp, width / 2 + 118, 26, width=68, height=68, mask="auto")

    c.line(15, 35, width - 15, 35)
    draw_text(32, 22, "서식3-J113Rev.0", 8.5, PDF_FONT)
    draw_center(width / 2, 22, "㈜삼양사 인천1공장", 8.5, PDF_FONT)
    draw_text(width - 158, 22, "A4(210mm X 297mm)", 8.5, PDF_FONT)

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
    product_data = df[df["product_code"] == product_code]

    if len(product_data) == 0:
        st.error("해당 제품을 찾을 수 없습니다.")
    else:
        product_name = product_data.iloc[0]["product_name"]
        st.title(f"{product_name} 인증서 / 확인서")
        st.write("필요한 문서를 체크한 뒤 ZIP으로 한 번에 다운로드할 수 있습니다.")

        all_docs_for_zip = []

        for idx, row in product_data.reset_index(drop=True).iterrows():
            cert_name = str(row["cert_name"])
            doc_type = str(row["type"]).strip().lower()
            safe_cert_name = cert_name.strip().replace(" ", "_")

            file_bytes = None
            output_file_name = None

            if doc_type == "file":
                file_name = row["file"] if "file" in row.index else ""

                if pd.isna(file_name) or str(file_name).strip() == "":
                    st.warning(f"{cert_name}: 파일명이 비어 있습니다.")
                    continue

                file_name = str(file_name).strip()
                file_path = os.path.join(FILES_DIR, file_name)

                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()

                    output_file_name = file_name

                    col1, col2 = st.columns([4, 2])

                    with col1:
                        checked = st.checkbox(
                            f"{cert_name} 선택",
                            key=f"check_file_{product_code}_{safe_cert_name}_{idx}",
                        )

                    with col2:
                        st.download_button(
                            label=f"{cert_name} 다운로드",
                            data=file_bytes,
                            file_name=output_file_name,
                            mime="application/pdf",
                            key=f"file_{product_code}_{safe_cert_name}_{idx}",
                        )

                    all_docs_for_zip.append((output_file_name, file_bytes, checked))
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
                    receiver = "수신자제위"

                    if "main_ingredient" in row.index and not pd.isna(row["main_ingredient"]):
                        main_ingredient = str(row["main_ingredient"]).strip()

                    if "origin_country" in row.index and not pd.isna(row["origin_country"]):
                        origin_country = str(row["origin_country"]).strip()

                    if "receiver" in row.index and not pd.isna(row["receiver"]):
                        receiver = str(row["receiver"]).strip()

                    pdf_data = generate_origin_certificate_pdf(
                        product_name=product_name,
                        main_ingredient=main_ingredient,
                        origin_country=origin_country,
                        receiver=receiver,
                    )
                else:
                    pdf_data = generate_template_pdf(product_name, template_type)

                file_bytes = pdf_data.getvalue()
                output_file_name = f"{product_name}_{cert_name}_{datetime.today().strftime('%Y%m%d')}.pdf"

                col1, col2 = st.columns([4, 2])

                with col1:
                    checked = st.checkbox(
                        f"{cert_name} 선택",
                        key=f"check_template_{product_code}_{safe_cert_name}_{template_type}_{idx}",
                    )

                with col2:
                    st.download_button(
                        label=f"{cert_name} 발급",
                        data=file_bytes,
                        file_name=output_file_name,
                        mime="application/pdf",
                        key=f"template_{product_code}_{safe_cert_name}_{template_type}_{idx}",
                    )

                all_docs_for_zip.append((output_file_name, file_bytes, checked))

            else:
                st.warning(f"{cert_name}: type 값이 올바르지 않습니다.")

        selected_docs = [
            (file_name, file_bytes)
            for file_name, file_bytes, checked in all_docs_for_zip
            if checked
        ]

        if all_docs_for_zip:
            st.divider()
            st.subheader("선택 문서 일괄 다운로드")

            if selected_docs:
                zip_buffer = build_zip_from_documents(selected_docs)

                st.download_button(
                    label="선택한 문서 ZIP 다운로드",
                    data=zip_buffer,
                    file_name=f"{product_name}_certificates_{datetime.today().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                    key=f"zip_{product_code}",
                )
            else:
                st.info("ZIP으로 받을 문서를 체크해주세요.")

else:
    st.title("제품별 인증서 / 확인서")
    st.write("제품을 선택하세요.")

    products = df[["product_code", "product_name"]].drop_duplicates()

    for _, row in products.iterrows():
        st.markdown(f"- [{row['product_name']}](?product={row['product_code']})")
