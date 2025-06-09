import os
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
import logging

load_dotenv()
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

def get_or_create_container(user_id: str):
    container_name = f"user-{user_id.lower()}"
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.get_container_properties()
    except Exception:
        container_client = blob_service_client.create_container(container_name)
    return container_client

def upload_image(user_id: str, filename: str, content: bytes):
    container_client = get_or_create_container(user_id)
    blob_path = f"images/{filename}"  # Save under images/ folder
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.upload_blob(content, overwrite=True)


def delete_image(user_id: str, filename: str):
    container_client = get_or_create_container(user_id)
    blob_path = f"images/{filename}"
    blob_client = container_client.get_blob_client(blob_path)
    blob_client.delete_blob()


def list_images(user_id: str):
    container_client = get_or_create_container(user_id)
    prefix = "images/"
    return [
        blob.name[len(prefix):] for blob in container_client.list_blobs(name_starts_with=prefix)
    ]

def get_image_sas_url(user_id: str, filename: str, expiry_minutes: int = 30) -> str:
    container_name = f"user-{user_id.lower()}"
    blob_path = f"images/{filename}"
    sas_token = generate_blob_sas(
        account_name=AZURE_STORAGE_ACCOUNT_NAME,
        container_name=container_name,
        blob_name=blob_path,
        account_key=AZURE_STORAGE_ACCOUNT_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes)
    )
    return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container_name}/{blob_path}?{sas_token}"

# tss/stt azure utils

# 로깅 설정
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "user"

if not AZURE_CONNECTION_STRING:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING 환경 변수가 설정되지 않았습니다.")

# Azure Blob Service 클라이언트 초기화
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

def get_or_create_container() -> ContainerClient:
    """
    컨테이너를 가져오거나 없으면 생성합니다.
    
    Returns:
        ContainerClient: 컨테이너 클라이언트
    """
    try:
        # 컨테이너 존재 확인
        container_client.get_container_properties()
        logger.info(f"컨테이너 '{CONTAINER_NAME}' 존재 확인됨")
    except ResourceNotFoundError:
        # 컨테이너가 없으면 생성
        try:
            blob_service_client.create_container(CONTAINER_NAME)
            logger.info(f"컨테이너 '{CONTAINER_NAME}' 생성 완료")
        except ResourceExistsError:
            # 동시에 생성된 경우 무시
            logger.info(f"컨테이너 '{CONTAINER_NAME}' 이미 존재함")
        except Exception as e:
            logger.error(f"컨테이너 생성 실패: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"컨테이너 확인 중 오류: {str(e)}")
        raise
    
    return container_client

def blob_prefix_exists(container_client: ContainerClient, prefix: str) -> bool:
    """
    특정 prefix(폴더 경로)가 컨테이너에 존재하는지 확인합니다.
    
    Args:
        container_client: 컨테이너 클라이언트
        prefix: 확인할 prefix
        
    Returns:
        bool: prefix 존재 여부
    """
    try:
        blobs = list(container_client.list_blobs(name_starts_with=prefix))
        exists = len(blobs) > 0
        logger.debug(f"Prefix '{prefix}' 존재 여부: {exists}")
        return exists
    except Exception as e:
        logger.error(f"Prefix 확인 중 오류: {str(e)}")
        return False

def get_unique_blob_name(container_client: ContainerClient, base_path: str, filename: str) -> str:
    """
    중복되지 않는 고유한 blob 이름을 생성합니다.
    
    Args:
        container_client: 컨테이너 클라이언트
        base_path: 기본 경로
        filename: 파일명
        
    Returns:
        str: 고유한 blob 경로
    """
    name, ext = os.path.splitext(filename)
    counter = 0
    new_filename = filename
    full_path = f"{base_path}/{new_filename}"
    
    try:
        while container_client.get_blob_client(full_path).exists():
            counter += 1
            new_filename = f"{name}_{counter}{ext}"
            full_path = f"{base_path}/{new_filename}"
            
            # 무한 루프 방지
            if counter > 1000:
                current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{name}_{current_time}{ext}"
                full_path = f"{base_path}/{new_filename}"
                break
                
        logger.info(f"고유한 blob 이름 생성: {full_path}")
        return full_path
        
    except Exception as e:
        logger.error(f"고유한 blob 이름 생성 중 오류: {str(e)}")
        # 오류 발생 시 타임스탬프 기반 이름 반환
        current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fallback_name = f"{name}_{current_time}{ext}"
        return f"{base_path}/{fallback_name}"

def upload_interview_result(user_id: str, folder_name: str, content: str) -> str:
    """
    인터뷰 결과를 Azure Blob Storage에 업로드합니다.
    
    Args:
        user_id: 사용자 ID
        folder_name: 폴더명
        content: 업로드할 텍스트 내용
        
    Returns:
        str: 업로드된 blob의 경로
        
    Raises:
        ValueError: 입력 파라미터가 유효하지 않은 경우
        Exception: Azure Storage 관련 오류
    """
    # 입력 유효성 검사
    if not user_id or not user_id.strip():
        raise ValueError("사용자 ID가 필요합니다.")
    if not folder_name or not folder_name.strip():
        raise ValueError("폴더명이 필요합니다.")
    if not content or not content.strip():
        raise ValueError("내용이 필요합니다.")
    
    try:
        # 컨테이너 가져오기 또는 생성
        container_client = get_or_create_container()
        
        # 현재 날짜로 파일명 생성
        current_date = datetime.datetime.now()
        filename = f"interview_{current_date.month:02d}-{current_date.day:02d}.txt"
        
        # user/{userid}/magazine/{foldername}/texts/ 경로 생성
        base_path = f"{user_id.strip()}/magazine/{folder_name.strip()}/texts"
        
        # 중복된 파일명 방지
        blob_path = get_unique_blob_name(container_client, base_path, filename)
        blob_client = container_client.get_blob_client(blob_path)
        
        # 문자열을 UTF-8로 인코딩하여 업로드
        content_bytes = content.encode('utf-8')
        blob_client.upload_blob(
            content_bytes, 
            overwrite=True,
            content_settings=ContentSettings(
                content_type='text/plain; charset=utf-8',
                content_encoding='utf-8'
            )
        )
        
        logger.info(f"인터뷰 결과 업로드 완료: {blob_path}")
        return blob_path
        
    except ValueError:
        # 입력 유효성 오류는 그대로 전파
        raise
    except Exception as e:
        logger.error(f"인터뷰 결과 업로드 실패: {str(e)}")
        raise Exception(f"Azure Storage 업로드 실패: {str(e)}")

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
        logger.info(f"사용자 {user_id}의 폴더 목록: {folder_list}")
        return folder_list
        
    except Exception as e:
        logger.error(f"폴더 목록 조회 실패: {str(e)}")
        return []

def download_interview_result(user_id: str, folder_name: str, filename: str) -> str:
    """
    저장된 인터뷰 결과를 다운로드합니다.
    
    Args:
        user_id: 사용자 ID
        folder_name: 폴더명
        filename: 파일명
        
    Returns:
        str: 파일 내용
    """
    try:
        container_client = get_or_create_container()
        blob_path = f"{user_id}/magazine/{folder_name}/texts/{filename}"
        blob_client = container_client.get_blob_client(blob_path)
        
        content = blob_client.download_blob().readall()
        return content.decode('utf-8')
        
    except ResourceNotFoundError:
        logger.warning(f"파일을 찾을 수 없음: {blob_path}")
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {filename}")
    except Exception as e:
        logger.error(f"파일 다운로드 실패: {str(e)}")
        raise Exception(f"파일 다운로드 실패: {str(e)}")

def delete_interview_result(user_id: str, folder_name: str, filename: str) -> bool:
    """
    저장된 인터뷰 결과를 삭제합니다.
    
    Args:
        user_id: 사용자 ID
        folder_name: 폴더명
        filename: 파일명
        
    Returns:
        bool: 삭제 성공 여부
    """
    try:
        container_client = get_or_create_container()
        blob_path = f"{user_id}/magazine/{folder_name}/texts/{filename}"
        blob_client = container_client.get_blob_client(blob_path)
        
        blob_client.delete_blob()
        logger.info(f"파일 삭제 완료: {blob_path}")
        return True
        
    except ResourceNotFoundError:
        logger.warning(f"삭제할 파일을 찾을 수 없음: {blob_path}")
        return False
    except Exception as e:
        logger.error(f"파일 삭제 실패: {str(e)}")
        return False