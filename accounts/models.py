from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # traveler_id를 기본 ID로 사용하기 위해 username을 traveler_id로 설정
    username = models.CharField(max_length=100, unique=True, primary_key=True, db_index=True)  # traveler_id
    # e009688, e003836

    profile_image = models.ImageField("프로필 이미지", upload_to="account/profile", blank=True, null=True)
    short_description = models.TextField('소개글', blank=True)

    # 여행객 정보 필드 추가
    residence_area = models.CharField(max_length=100, null=True, blank=True)  # 거주 지역
    gender = models.CharField(max_length=10, null=True, blank=True)  # 성별
    age = models.IntegerField(null=True, blank=True)  # 나이

    def __str__(self):
        return self.username  # 사용자 이름을 기본 출력으로 설정
