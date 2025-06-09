import os
from azure.storage.blob import BlobServiceClient, ContainerClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeImageOptions, ImageData, ImageCategory
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError, HttpResponseError
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Get the directory where azure_utils.py is located
current_dir = Path(__file__).parent
env_path = current_dir / '.env'

print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

load_dotenv(env_path, override=True)

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

CONTENT_SAFETY_ENDPOINT = os.getenv("CONTENT_SAFETY_ENDPOINT", "").strip().strip("'\"").rstrip("/")
CONTENT_SAFETY_KEY = os.getenv("CONTENT_SAFETY_KEY", "").strip().strip("'\"").rstrip("/")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

def get_or_create_container():
    container_name = "user"
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.get_container_properties()
    except Exception:
        container_client = blob_service_client.create_container(container_name)
    return container_client

def build_blob_path(user_id: str, magazine_id: str, category: str, filename: str) -> str:
    return f"{user_id}/magazine/{magazine_id}/{category}/{filename}"

def upload_image_if_not_exists(user_id: str, magazine_id: str, filename: str, content: bytes) -> bool:
    container_client = get_or_create_container()
    blob_path = build_blob_path(user_id, magazine_id, "images", filename)
    blob_client = container_client.get_blob_client(blob_path)
    if blob_client.exists():
        return False
    blob_client.upload_blob(content, overwrite=False)
    return True

def delete_image(user_id: str, magazine_id: str, filename: str):
    container_client = get_or_create_container()
    blob_path = build_blob_path(user_id, magazine_id, "images", filename)
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.delete_blob()

def list_images(user_id: str, magazine_id: str):
    container_client = get_or_create_container()
    prefix = f"{user_id}/magazine/{magazine_id}/images/"
    return [blob.name[len(prefix):] for blob in container_client.list_blobs(name_starts_with=prefix)]

def generate_blob_sas_url(user_id: str, magazine_id: str, category: str, filename: str, expiry_minutes: int = 30) -> str:
    blob_path = build_blob_path(user_id, magazine_id, category, filename)
    sas_token = generate_blob_sas(
        account_name=AZURE_STORAGE_ACCOUNT_NAME,
        container_name="user",
        blob_name=blob_path,
        account_key=AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    )
    return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/user/{blob_path}?{sas_token}"


def list_output_files(user_id: str, magazine_id: str):
    container_client = get_or_create_container()
    prefix = f"{user_id}/magazine/{magazine_id}/outputs/"
    return [blob.name[len(prefix):] for blob in container_client.list_blobs(name_starts_with=prefix)]

def upload_output_file(user_id: str, magazine_id: str, filename: str, content: bytes):
    container_client = get_or_create_container()
    blob_path = build_blob_path(user_id, magazine_id, "outputs", filename)
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.upload_blob(content, overwrite=True)


def analyze_image_from_blob(image_content: bytes, filename: str = "") -> dict:
    """
    Analyze image content using Azure Content Safety API.
    Returns result dict including 'should_filter' flag and per-category analysis.
    """
    if not CONTENT_SAFETY_ENDPOINT or not CONTENT_SAFETY_KEY:
        raise ValueError("Content Safety endpoint and key must be configured")
    
    print(f"Using Content Safety endpoint: {CONTENT_SAFETY_ENDPOINT}")
    print(f"Content Safety key configured: {'Yes' if CONTENT_SAFETY_KEY else 'No'}")
    
    client = ContentSafetyClient(
        endpoint=CONTENT_SAFETY_ENDPOINT,
        credential=AzureKeyCredential(CONTENT_SAFETY_KEY)
    )

    # Create the request with proper image data
    image_data = ImageData(content=image_content)
    request = AnalyzeImageOptions(image=image_data)

    try:
        print(f"Analyzing image: {filename} ({len(image_content)} bytes)")
        response = client.analyze_image(request)
        print(f"Analysis successful for {filename}")
    except HttpResponseError as e:
        print(f"Content Safety API error for {filename}: {e}")
        print(f"Status code: {e.status_code}")
        print(f"Error code: {e.error.code if hasattr(e, 'error') and e.error else 'Unknown'}")
        print(f"Error message: {e.error.message if hasattr(e, 'error') and e.error else str(e)}")
        raise
    except Exception as e:
        print(f"Unexpected error analyzing {filename}: {e}")
        raise

    results = {
        "filename": filename,
        "image_size": len(image_content),
        "analysis": {},
        "should_filter": False
    }

    categories = [
        ("hate", ImageCategory.HATE),
        ("self_harm", ImageCategory.SELF_HARM),
        ("sexual", ImageCategory.SEXUAL),
        ("violence", ImageCategory.VIOLENCE)
    ]

    for name, cat_enum in categories:
        cat_result = next((c for c in response.categories_analysis if c.category == cat_enum), None)
        severity = cat_result.severity if cat_result else 0
        filtered = severity > 2
        results["analysis"][name] = {
            "severity": severity,
            "filtered": filtered
        }
        if filtered:
            results["should_filter"] = True

    return results
# def analyze_image_from_blob(image_content: bytes, filename: str = "") -> dict:
#     """
#     Analyze image content using Azure Content Safety API.
#     Returns result dict including 'should_filter' flag and per-category analysis.
#     """
#     client = ContentSafetyClient(
#         endpoint=CONTENT_SAFETY_ENDPOINT,
#         credential=AzureKeyCredential(CONTENT_SAFETY_KEY)
#     )

#     request = AnalyzeImageOptions(image=ImageData(content=image_content))

#     try:
#         response = client.analyze_image(request)
#     except HttpResponseError as e:
#         print(f"Content Safety API error for {filename}: {e}")
#         raise

#     results = {
#         "filename": filename,
#         "image_size": len(image_content),
#         "analysis": {},
#         "should_filter": False
#     }

#     categories = [
#         ("hate", ImageCategory.HATE),
#         ("self_harm", ImageCategory.SELF_HARM),
#         ("sexual", ImageCategory.SEXUAL),
#         ("violence", ImageCategory.VIOLENCE)
#     ]

#     for name, cat_enum in categories:
#         cat_result = next((c for c in response.categories_analysis if c.category == cat_enum), None)
#         severity = cat_result.severity if cat_result else 0
#         filtered = severity > 2
#         results["analysis"][name] = {
#             "severity": severity,
#             "filtered": filtered
#         }
#         if filtered:
#             results["should_filter"] = True

#     return results

def is_image_safe_for_upload(image_bytes: bytes, filename: str = "") -> tuple[bool, dict]:
    try:
        result = analyze_image_from_blob(image_bytes, filename)
        return not result["should_filter"], result
    except Exception as e:
        return False, {"error": str(e)}


def upload_profile_image(user_id: str, content: bytes, filename: str = "profile_image.jpg") -> str:
    """
    Uploads the user's profile image to Azure Blob Storage and returns the blob URL.
    """
    container_client = get_or_create_container()
    blob_path = f"{user_id}/profile/image/{filename}"
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.upload_blob(content, overwrite=True)

    sas_token = generate_blob_sas(
        account_name=AZURE_STORAGE_ACCOUNT_NAME,
        container_name="user",
        blob_name=blob_path,
        account_key=AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(hours=1)
    )

    return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/user/{blob_path}?{sas_token}"

def upload_interview_result(user_id: str, magazine_id: str, filename: str, content: bytes):
    container_client = get_or_create_container()
    blob_path = build_blob_path(user_id, magazine_id, "texts", filename)
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.upload_blob(content, overwrite=True, content_settings=ContentSettings(content_type="text/plain"))
    return blob_path

# def upload_interview_result(user_id: str, folder_name: str, content: str) -> str:
#     """
#     인터뷰 결과를 Azure Blob Storage에 업로드합니다.
    
#     Args:
#         user_id: 사용자 ID
#         folder_name: 폴더명
#         content: 업로드할 텍스트 내용
        
#     Returns:
#         str: 업로드된 blob의 경로
        
#     Raises:
#         ValueError: 입력 파라미터가 유효하지 않은 경우
#         Exception: Azure Storage 관련 오류
#     """
#     # 입력 유효성 검사
#     if not user_id or not user_id.strip():
#         raise ValueError("사용자 ID가 필요합니다.")
#     if not folder_name or not folder_name.strip():
#         raise ValueError("폴더명이 필요합니다.")
#     if not content or not content.strip():
#         raise ValueError("내용이 필요합니다.")
    
#     try:
#         # 컨테이너 가져오기 또는 생성
#         container_client = get_or_create_container()
        
#         # 현재 날짜로 파일명 생성
#         current_date = datetime.datetime.now()
#         filename = f"interview_{current_date.month:02d}-{current_date.day:02d}.txt"
        
#         # user/{userid}/magazine/{foldername}/texts/ 경로 생성
#         base_path = f"{user_id.strip()}/magazine/{folder_name.strip()}/texts"
        
#         # 중복된 파일명 방지
#         blob_path = get_unique_blob_name(container_client, base_path, filename)
#         blob_client = container_client.get_blob_client(blob_path)
        
#         # 문자열을 UTF-8로 인코딩하여 업로드
#         content_bytes = content.encode('utf-8')
#         blob_client.upload_blob(
#             content_bytes, 
#             overwrite=True,
#             content_settings=ContentSettings(
#                 content_type='text/plain; charset=utf-8',
#                 content_encoding='utf-8'
#             )
#         )
        
#         logger.info(f"인터뷰 결과 업로드 완료: {blob_path}")
#         return blob_path
        
#     except ValueError:
#         # 입력 유효성 오류는 그대로 전파
#         raise
#     except Exception as e:
#         logger.error(f"인터뷰 결과 업로드 실패: {str(e)}")
#         raise Exception(f"Azure Storage 업로드 실패: {str(e)}")

def list_user_folders(user_id: str) -> list:
    """
    특정 사용자의 magazine 폴더 목록을 반환합니다.
    
    Args:
        user_id: 사용자 ID
        
    Returns:
        list: 폴더명 목록
    """
    try:
        container_client = get_or_create_container()
        prefix = f"{user_id}/magazine/"
        
        folders = set()
        blobs = container_client.list_blobs(name_starts_with=prefix)
        
        for blob in blobs:
            # magazine/ 다음 부분을 추출
            relative_path = blob.name[len(prefix):]
            if '/' in relative_path:
                folder_name = relative_path.split('/')[0]
                folders.add(folder_name)
        
        folder_list = sorted(list(folders))
        #logger.info(f"사용자 {user_id}의 폴더 목록: {folder_list}")
        return folder_list

       
    #except Exception as e:
        #logger.error(f"폴더 목록 조회 실패: {str(e)}")
    except Exception:
        return []

def download_interview_result(user_id: str, magazine_id: str, filename: str) -> str:
    container_client = get_or_create_container()
    blob_path = build_blob_path(user_id, magazine_id, "texts", filename)
    blob_client = container_client.get_blob_client(blob_path)
    try:
        content = blob_client.download_blob().readall()
        return content.decode("utf-8")
    except ResourceNotFoundError:
        raise FileNotFoundError(f"File not found: {blob_path}")

# def download_interview_result(user_id: str, folder_name: str, filename: str) -> str:
#     """
#     저장된 인터뷰 결과를 다운로드합니다.
    
#     Args:
#         user_id: 사용자 ID
#         folder_name: 폴더명
#         filename: 파일명
        
#     Returns:
#         str: 파일 내용
#     """
#     try:
#         container_client = get_or_create_container()
#         blob_path = f"{user_id}/magazine/{folder_name}/texts/{filename}"
#         blob_client = container_client.get_blob_client(blob_path)
        
#         content = blob_client.download_blob().readall()
#         return content.decode('utf-8')
        
#     except ResourceNotFoundError:
#         logger.warning(f"파일을 찾을 수 없음: {blob_path}")
#         raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filename}")
#     except Exception as e:
#         logger.error(f"파일 다운로드 실패: {str(e)}")
#         raise Exception(f"파일 다운로드 실패: {str(e)}")

def delete_interview_result(user_id: str, magazine_id: str, filename: str) -> bool:
    container_client = get_or_create_container()
    blob_path = build_blob_path(user_id, magazine_id, "texts", filename)
    blob_client = container_client.get_blob_client(blob_path)
    try:
        blob_client.delete_blob()
        return True
    except ResourceNotFoundError:
        return False

# def delete_interview_result(user_id: str, folder_name: str, filename: str) -> bool:
#     """
#     저장된 인터뷰 결과를 삭제합니다.
    
#     Args:
#         user_id: 사용자 ID
#         folder_name: 폴더명
#         filename: 파일명
        
#     Returns:
#         bool: 삭제 성공 여부
#     """
#     try:
#         container_client = get_or_create_container()
#         blob_path = f"{user_id}/magazine/{folder_name}/texts/{filename}"
#         blob_client = container_client.get_blob_client(blob_path)
        
#         blob_client.delete_blob()
#         logger.info(f"파일 삭제 완료: {blob_path}")
#         return True
        
#     except ResourceNotFoundError:
#         logger.warning(f"삭제할 파일을 찾을 수 없음: {blob_path}")
#         return False
#     except Exception as e:
#         logger.error(f"파일 삭제 실패: {str(e)}")
#         return False

def list_text_files(user_id: str, magazine_id: str):
    container_client = get_or_create_container()
    prefix = f"{user_id}/magazine/{magazine_id}/texts/"
    return [blob.name[len(prefix):] for blob in container_client.list_blobs(name_starts_with=prefix)]