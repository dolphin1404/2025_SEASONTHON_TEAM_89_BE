import random
import string
from datetime import datetime
from typing import Optional, List, Dict
from app.schemas.family_group import (
    FamilyGroupCreateRequest, 
    FamilyGroupCreateResponse,
    FamilyGroupJoinRequest,
    FamilyGroupJoinResponse,
    FamilyGroupInfoResponse,
    FamilyMember
)

class FamilyGroupService:
    def __init__(self):
        # TODO 현재는 메모리 기반 저장소 사용 -> DB로 변경해야함
        self.groups: Dict[str, dict] = {}  # group_id -> group_data
        self.join_codes: Dict[str, str] = {}  # join_code -> group_id
        self.user_groups: Dict[str, str] = {}  # user_id -> group_id
        self.user_warnings: Dict[str, int] = {}  # user_id -> warning_count
    
    def _generate_group_id(self) -> str:
        """고유한 그룹 ID 생성"""
        return f"group_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
    
    def _generate_join_code(self) -> str:
        """10자리 참여 코드 생성"""
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if code not in self.join_codes:
                return code
    
    def create_family_group(self, request: FamilyGroupCreateRequest) -> FamilyGroupCreateResponse:
        """가족 그룹 생성"""
        # 사용자가 이미 그룹에 속해있는지 확인
        if request.user_id in self.user_groups:
            raise ValueError("USER_ALREADY_IN_GROUP")
        
        # 그룹 ID와 참여 코드 생성
        group_id = self._generate_group_id()
        join_code = self._generate_join_code()
        created_at = datetime.now()
        
        # 그룹 데이터 저장
        group_data = {
            "group_id": group_id,
            "group_name": request.group_name,
            "creator_id": request.user_id,
            "creator_name": request.user_name,
            "members": {
                request.user_id: {
                    "user_id": request.user_id,
                    "user_name": request.user_name,
                    "is_creator": True,
                    "joined_at": created_at
                }
            },
            "created_at": created_at
        }
        
        self.groups[group_id] = group_data
        self.join_codes[join_code] = group_id
        self.user_groups[request.user_id] = group_id
        
        # 사용자 경고 횟수 초기화 (없으면)
        if request.user_id not in self.user_warnings:
            self.user_warnings[request.user_id] = 0
        
        return FamilyGroupCreateResponse(
            group_id=group_id,
            group_name=request.group_name,
            join_code=join_code,
            creator_id=request.user_id,
            created_at=created_at
        )
    
    def join_family_group(self, request: FamilyGroupJoinRequest) -> FamilyGroupJoinResponse:
        """가족 그룹 참여"""
        # 사용자가 이미 그룹에 속해있는지 확인
        if request.user_id in self.user_groups:
            raise ValueError("USER_ALREADY_IN_GROUP")
        
        # 참여 코드가 유효한지 확인
        if request.join_code not in self.join_codes:
            raise ValueError("INVALID_JOIN_CODE")
        
        group_id = self.join_codes[request.join_code]
        group_data = self.groups[group_id]
        joined_at = datetime.now()
        
        # 그룹에 멤버 추가
        group_data["members"][request.user_id] = {
            "user_id": request.user_id,
            "user_name": request.user_name,
            "is_creator": False,
            "joined_at": joined_at
        }
        
        self.user_groups[request.user_id] = group_id
        
        # 사용자 경고 횟수 초기화 (없으면)
        if request.user_id not in self.user_warnings:
            self.user_warnings[request.user_id] = 0
        
        return FamilyGroupJoinResponse(
            group_id=group_id,
            group_name=group_data["group_name"],
            creator_name=group_data["creator_name"],
            joined_at=joined_at
        )
    
    def get_family_group_info(self, user_id: str) -> Optional[FamilyGroupInfoResponse]:
        """사용자의 가족 그룹 정보 조회"""
        if user_id not in self.user_groups:
            return None
        
        group_id = self.user_groups[user_id]
        group_data = self.groups[group_id]
        
        # 구성원 리스트 생성
        members = []
        for member_data in group_data["members"].values():
            warning_count = self.user_warnings.get(member_data["user_id"], 0)
            members.append(FamilyMember(
                user_id=member_data["user_id"],
                user_name=member_data["user_name"],
                warning_count=warning_count,
                is_creator=member_data["is_creator"],
                joined_at=member_data["joined_at"]
            ))
        
        # 그룹장 순으로 정렬
        members.sort(key=lambda x: (not x.is_creator, x.joined_at))
        
        return FamilyGroupInfoResponse(
            group_id=group_id,
            group_name=group_data["group_name"],
            member_count=len(members),
            members=members,
            created_at=group_data["created_at"]
        )
    
    def update_user_warning_count(self, user_id: str, warning_count: int):
        """사용자 경고 횟수 업데이트 (다른 시스템에서 호출)"""
        self.user_warnings[user_id] = warning_count
    
    def leave_family_group(self, user_id: str) -> bool:
        """가족 그룹 탈퇴"""
        if user_id not in self.user_groups:
            return False
        
        group_id = self.user_groups[user_id]
        group_data = self.groups[group_id]
        
        # 그룹장이 탈퇴하는 경우
        if group_data["creator_id"] == user_id:
            # 그룹 해체 (모든 멤버 제거)
            for member_id in list(group_data["members"].keys()):
                if member_id in self.user_groups:
                    del self.user_groups[member_id]
            
            # 그룹 데이터 제거
            del self.groups[group_id]
            
            # 참여 코드 제거
            join_code_to_remove = None
            for code, gid in self.join_codes.items():
                if gid == group_id:
                    join_code_to_remove = code
                    break
            if join_code_to_remove:
                del self.join_codes[join_code_to_remove]
        else:
            # 일반 멤버 탈퇴
            del group_data["members"][user_id]
            del self.user_groups[user_id]
        
        return True

# 싱글톤 서비스 인스턴스
family_group_service = FamilyGroupService()
