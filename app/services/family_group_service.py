import random
import string
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set
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
        
        # 임시 그룹 생성 대기 시스템
        self.pending_groups: Dict[str, dict] = {}  # join_code -> pending_group_data
        self.pending_codes: Dict[str, str] = {}  # user_id -> join_code (생성자만)
        self.waiting_users: Dict[str, Set[str]] = {}  # join_code -> set of user_ids
        self.group_timers: Dict[str, asyncio.Task] = {}  # join_code -> timer_task
    
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
        """가족 그룹 생성 대기 상태로 시작"""
        # 사용자가 이미 그룹에 속해있는지 확인
        if request.user_id in self.user_groups:
            raise ValueError("USER_ALREADY_IN_GROUP")
            
        # 이미 대기 중인 그룹이 있는지 확인
        if request.user_id in self.pending_codes:
            raise ValueError("ALREADY_CREATING_GROUP")
        
        # 참여 코드 생성
        join_code = self._generate_join_code()
        created_at = datetime.now()
        
        # 임시 그룹 데이터 저장 (아직 완성되지 않은 상태)
        pending_group_data = {
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
            "created_at": created_at,
            "status": "pending"  # pending, completed, expired
        }
        
        self.pending_groups[join_code] = pending_group_data
        self.pending_codes[request.user_id] = join_code
        self.waiting_users[join_code] = {request.user_id}
        
        # 5분 타이머 시작
        timer_task = asyncio.create_task(self._expire_group_creation(join_code))
        self.group_timers[join_code] = timer_task
        
        return FamilyGroupCreateResponse(
            group_id=f"pending_{join_code}",  # 임시 ID
            group_name=request.group_name,
            join_code=join_code,
            creator_id=request.user_id,
            created_at=created_at
        )
    
    def join_family_group(self, request: FamilyGroupJoinRequest) -> FamilyGroupJoinResponse:
        """가족 그룹 참여 (대기 중인 그룹에 참여)"""
        # 사용자가 이미 그룹에 속해있는지 확인
        if request.user_id in self.user_groups:
            raise ValueError("USER_ALREADY_IN_GROUP")
        
        # 대기 중인 그룹 참여 코드인지 확인
        if request.join_code in self.pending_groups:
            return self._join_pending_group(request)
        
        # 완성된 그룹 참여 코드인지 확인
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
    
    def _join_pending_group(self, request: FamilyGroupJoinRequest) -> FamilyGroupJoinResponse:
        """대기 중인 그룹에 참여"""
        join_code = request.join_code
        pending_group = self.pending_groups[join_code]
        joined_at = datetime.now()
        
        # 대기 중인 그룹에 멤버 추가
        pending_group["members"][request.user_id] = {
            "user_id": request.user_id,
            "user_name": request.user_name,
            "is_creator": False,
            "joined_at": joined_at
        }
        
        # 대기 사용자 목록에 추가
        self.waiting_users[join_code].add(request.user_id)
        
        # 🆕 마지막 업데이트 시간 추가 (폴링용)
        pending_group["last_updated"] = joined_at
        
        return FamilyGroupJoinResponse(
            group_id=f"pending_{join_code}",
            group_name=pending_group["group_name"],
            creator_name=pending_group["creator_name"],
            joined_at=joined_at
        )
    
    async def complete_group_creation(self, user_id: str) -> dict:
        """그룹 생성 완료 (생성자만 가능)"""
        if user_id not in self.pending_codes:
            raise ValueError("NO_PENDING_GROUP")
        
        join_code = self.pending_codes[user_id]
        pending_group = self.pending_groups[join_code]
        
        if pending_group["creator_id"] != user_id:
            raise ValueError("NOT_GROUP_CREATOR")
        
        # 실제 그룹 생성
        group_id = self._generate_group_id()
        group_data = {
            "group_id": group_id,
            "group_name": pending_group["group_name"],
            "creator_id": pending_group["creator_id"],
            "creator_name": pending_group["creator_name"],
            "members": pending_group["members"],
            "created_at": pending_group["created_at"]
        }
        
        # 정식 그룹으로 이동
        self.groups[group_id] = group_data
        self.join_codes[join_code] = group_id
        
        # 모든 멤버를 정식 그룹에 등록
        for member_id in pending_group["members"]:
            self.user_groups[member_id] = group_id
            if member_id not in self.user_warnings:
                self.user_warnings[member_id] = 0
        
        # 타이머 취소
        if join_code in self.group_timers:
            self.group_timers[join_code].cancel()
            del self.group_timers[join_code]
        
        # 대기 상태 정리
        del self.pending_groups[join_code]
        del self.pending_codes[user_id]
        del self.waiting_users[join_code]
        
        return {
            "group_id": group_id,
            "group_name": group_data["group_name"],
            "total_members": len(group_data["members"]),
            "status": "completed"
        }
    
    async def _expire_group_creation(self, join_code: str):
        """5분 후 그룹 생성 만료"""
        try:
            await asyncio.sleep(300)  # 5분 대기
            
            if join_code in self.pending_groups:
                pending_group = self.pending_groups[join_code]
                creator_id = pending_group["creator_id"]
                
                # 대기 상태 정리
                if join_code in self.pending_groups:
                    del self.pending_groups[join_code]
                if creator_id in self.pending_codes:
                    del self.pending_codes[creator_id]
                if join_code in self.waiting_users:
                    del self.waiting_users[join_code]
                if join_code in self.group_timers:
                    del self.group_timers[join_code]
                    
        except asyncio.CancelledError:
            # 타이머가 취소된 경우 (그룹이 완성된 경우)
            pass
    
    def get_pending_group_info(self, user_id: str) -> Optional[dict]:
        """사용자의 대기 중인 그룹 정보 조회"""
        if user_id in self.pending_codes:
            join_code = self.pending_codes[user_id]
            if join_code in self.pending_groups:
                pending_group = self.pending_groups[join_code]
                
                # datetime 객체를 문자열로 변환
                members_data = []
                for member in pending_group["members"].values():
                    member_copy = member.copy()
                    member_copy["joined_at"] = member["joined_at"].isoformat()
                    members_data.append(member_copy)
                
                return {
                    "join_code": join_code,
                    "group_name": pending_group["group_name"],
                    "creator_id": pending_group["creator_id"],
                    "members": members_data,
                    "total_members": len(pending_group["members"]),
                    "status": "pending",
                    "created_at": pending_group["created_at"].isoformat()
                }
        
        # 참여 중인 대기 그룹 확인
        for join_code, user_set in self.waiting_users.items():
            if user_id in user_set and join_code in self.pending_groups:
                pending_group = self.pending_groups[join_code]
                
                # datetime 객체를 문자열로 변환
                members_data = []
                for member in pending_group["members"].values():
                    member_copy = member.copy()
                    member_copy["joined_at"] = member["joined_at"].isoformat()
                    members_data.append(member_copy)
                
                return {
                    "join_code": join_code,
                    "group_name": pending_group["group_name"],
                    "creator_id": pending_group["creator_id"],
                    "members": members_data,
                    "total_members": len(pending_group["members"]),
                    "status": "pending",
                    "created_at": pending_group["created_at"].isoformat()
                }
        
        return None

# 싱글톤 서비스 인스턴스
family_group_service = FamilyGroupService()
