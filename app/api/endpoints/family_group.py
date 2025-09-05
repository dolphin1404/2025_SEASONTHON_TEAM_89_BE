from fastapi import APIRouter, HTTPException, status
from app.schemas.family_group import (
    FamilyGroupCreateRequest,
    FamilyGroupCreateResponse,
    FamilyGroupJoinRequest,
    FamilyGroupJoinResponse,
    FamilyGroupInfoResponse,
    ErrorResponse
)
from app.services.family_group_service import family_group_service

router = APIRouter()

@router.post(
    "/create",
    response_model=FamilyGroupCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="가족 그룹 생성",
    description="새로운 가족 그룹을 생성 및 10자리 참여 코드를 발급"
)
async def create_family_group(request: FamilyGroupCreateRequest):
    """
    가족 그룹 생성 API
    
    - **group_name**: 그룹 이름 (최대 8자)
    - **user_id**: 그룹을 생성하는 사용자 ID
    - **user_name**: 그룹을 생성하는 사용자 이름
    
    Returns:
    - 생성된 그룹 정보와 10자리 참여 코드
    """
    try:
        result = family_group_service.create_family_group(request)
        return result
    except ValueError as e:
        error_code = str(e)
        if error_code == "USER_ALREADY_IN_GROUP":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가족 그룹에 속해있음"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="그룹 생성 실패"
        )

@router.post(
    "/join",
    response_model=FamilyGroupJoinResponse,
    status_code=status.HTTP_200_OK,
    summary="가족 그룹 참여",
    description="10자리 참여 코드를 사용하여 가족 그룹에 참여"
)
async def join_family_group(request: FamilyGroupJoinRequest):
    """
    가족 그룹 참여 API
    
    - **join_code**: 10자리 참여 코드
    - **user_id**: 참여하는 사용자 ID  
    - **user_name**: 참여하는 사용자 이름
    
    Returns:
    - 참여한 그룹 정보 (그룹명, 그룹장 이름 포함)
    """
    try:
        result = family_group_service.join_family_group(request)
        return result
    except ValueError as e:
        error_code = str(e)
        if error_code == "USER_ALREADY_IN_GROUP":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 가족 그룹에 속해있음"
            )
        elif error_code == "INVALID_JOIN_CODE":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="유효하지 않은 참여 코드"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="그룹 참여 실패"
        )

@router.get(
    "/info/{user_id}",
    response_model=FamilyGroupInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="가족 그룹 정보 조회",
    description="사용자가 속한 가족 그룹의 구성원 정보와 경고 횟수를 조회"
)
async def get_family_group_info(user_id: str):
    """
    가족 그룹 정보 조회 API
    
    - **user_id**: 조회하는 사용자 ID
    
    Returns:
    - 그룹 정보, 구성원 수, 각 구성원의 이름과 경고 횟수
    """
    result = family_group_service.get_family_group_info(user_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="가족 그룹에 속해있지 않음"
        )
    return result

@router.delete(
    "/leave/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="가족 그룹 탈퇴",
    description="가족 그룹에서 탈퇴 -> 그룹장이 탈퇴하면 그룹이 해체됨" 
    # TODO 이후 자동으로 승계하는 방법 고려할 수 있음
)
async def leave_family_group(user_id: str):
    """
    가족 그룹 탈퇴 API
    
    - **user_id**: 탈퇴하는 사용자 ID
    
    Note: 그룹장이 탈퇴하면 전체 그룹이 해체됨.
    """
    success = family_group_service.leave_family_group(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="가족 그룹에 속해있지 않음"
        )
    return {"message": "가족 그룹에서 탈퇴했습니다."}

@router.put(
    "/warning/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="사용자 경고 횟수 업데이트",
    description="사용자의 경고 횟수를 업데이트 (내부 시스템 호출용)"
)
async def update_warning_count(user_id: str, warning_count: int):
    """
    사용자 경고 횟수 업데이트 API (내부 시스템용)
    
    - **user_id**: 사용자 ID
    - **warning_count**: 새로운 경고 횟수
    """
    family_group_service.update_user_warning_count(user_id, warning_count)
    return {"message": f"사용자 {user_id}의 경고 횟수가 {warning_count}로 업데이트됨"}
