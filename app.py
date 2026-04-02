import streamlit as st
import pandas as pd
import os
import io
import zipfile

st.set_page_config(page_title="인증서 다운로드", layout="centered")

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "data", "certificates.csv")
FILES_DIR = os.path.join(BASE_DIR, "files")

# 데이터 불러오기
df = pd.read_csv(CSV_PATH)

# URL 파라미터 받기
query_params = st.query_params
product_code = query_params.get("product")

if product_code:
    product_data = df[df["product_code"] == product_code]

    if len(product_data) == 0:
        st.error("해당 제품을 찾을 수 없습니다.")
    else:
        product_name = product_data.iloc[0]["product_name"]
        st.title(f"{product_name} 인증서 다운로드")
        st.write("필요한 인증서를 선택한 뒤 다운로드하세요.")

        selected_files = []

        for idx, row in product_data.iterrows():
            cert_name = row["cert_name"]
            file_name = row["file"]

            if pd.isna(file_name):
                st.warning(f"{cert_name}: 파일 정보 없음")
                continue

            file_name = str(file_name)
            file_path = os.path.join(FILES_DIR, file_name)

            if not os.path.exists(file_path):
                st.warning(f"{cert_name}: 파일 없음 ({file_name})")
                continue

            checked = st.checkbox(
                f"{cert_name}",
                key=f"check_{product_code}_{idx}"
            )

            if checked:
                selected_files.append((file_name, file_path))

        st.write("---")

        if selected_files:
            # ZIP 파일 메모리 생성
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for file_name, file_path in selected_files:
                    zip_file.write(file_path, arcname=file_name)

            zip_buffer.seek(0)

            st.download_button(
                label="선택한 인증서 다운로드 (ZIP)",
                data=zip_buffer,
                file_name=f"{product_code}_certificates.zip",
                mime="application/zip"
            )
        else:
            st.info("다운로드할 인증서를 하나 이상 선택하세요.")

else:
    st.title("제품별 인증서 다운로드")
    st.write("제품을 선택하세요.")

    products = df[["product_code", "product_name"]].drop_duplicates()

    for _, row in products.iterrows():
        st.markdown(f"- [{row['product_name']}](?product={row['product_code']})")
