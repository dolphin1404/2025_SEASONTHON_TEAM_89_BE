from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

# 가족 그룹 생성 요청
class FamilyGroupCreateRequest(BaseModel):
    # group_name: str = Field(..., min_length=1, max_length=8, description="그룹 이름 (최대 8자)")
    user_id: str = Field(..., description="그룹을 생성하는 사용자 ID")
    user_name: str = Field(..., description="그룹을 생성하는 사용자 이름")

# 가족 그룹 생성 응답
class FamilyGroupCreateResponse(BaseModel):
    group_id: str = Field(..., description="생성된 그룹 ID")
    # group_name: str = Field(..., description="그룹 이름")
    join_code: str = Field(..., description="10자리 참여 코드")
    creator_id: str = Field(..., description="그룹장 ID")
    created_at: datetime = Field(..., description="생성 시간")

# 가족 그룹 참여 요청
class FamilyGroupJoinRequest(BaseModel):
    join_code: str = Field(..., min_length=10, max_length=10, description="10자리 참여 코드")
    user_id: str = Field(..., description="참여하는 사용자 ID")
    user_name: str = Field(..., description="참여하는 사용자 이름")

# 가족 그룹 참여 응답
class FamilyGroupJoinResponse(BaseModel):
    group_id: str = Field(..., description="참여한 그룹 ID")
    # group_name: str = Field(..., description="그룹 이름")
    creator_name: str = Field(..., description="그룹장 이름")
    joined_at: datetime = Field(..., description="참여 시간")

# 가족 구성원 정보
class FamilyMember(BaseModel):
    user_id: str = Field(..., description="사용자 ID")
    user_name: str = Field(..., description="사용자 이름")
    warning_count: int = Field(..., description="경고 받은 횟수")
    is_creator: bool = Field(..., description="그룹장 여부")
    joined_at: datetime = Field(..., description="그룹 참여 시간")

# 가족 그룹 정보 조회 응답
class FamilyGroupInfoResponse(BaseModel):
    group_id: str = Field(..., description="그룹 ID")
    # group_name: str = Field(..., description="그룹 이름")
    member_count: int = Field(..., description="구성원 수")
    members: List[FamilyMember] = Field(..., description="구성원 목록")
    created_at: datetime = Field(..., description="그룹 생성 시간")

# 가족 그룹 완료 응답
class FamilyGroupCompleteResponse(BaseModel):
    group_id: str = Field(..., description="완성된 그룹 ID")
    # group_name: str = Field(..., description="그룹 이름")
    creator_name: str = Field(..., description="그룹장 이름")
    members: List[str] = Field(..., description="구성원 목록")
    total_members: int = Field(..., description="총 멤버 수")
    completed_at: datetime = Field(..., description="완성 시간")

# 멤버 추방 요청
class FamilyGroupKickMemberRequest(BaseModel):
    creator_id: str = Field(..., description="그룹장 ID")
    target_user_id: str = Field(..., description="추방할 사용자 ID")

# 멤버 추방 응답
class FamilyGroupKickMemberResponse(BaseModel):
    success: bool = Field(..., description="추방 성공 여부")
    kicked_user_id: str = Field(..., description="추방된 사용자 ID")
    kicked_user_name: str = Field(..., description="추방된 사용자 이름")
    remaining_members: int = Field(..., description="남은 멤버 수")
    message: str = Field(..., description="결과 메시지")

# 에러 응답
class ErrorResponse(BaseModel):
    error: str = Field(..., description="에러 메시지")
    code: str = Field(..., description="에러 코드")
