from django.db import models
from django.core.exceptions import ValidationError
from accounts.models import User  # 기존의 커스터마이즈된 User 모델 사용


# 여행 목적 딕셔너리
TRAVEL_PURPOSE_CHOICES = [
    ("쇼핑", '쇼핑'),
    ("테마파크, 놀이시설, 동/식물원 방문", '테마파크, 놀이시설, 동/식물원 방문'),
    ("역사 유적지 방문", '역사 유적지 방문'),
    ("시티투어", '시티투어'),
    ("야외 스포츠, 레포츠 활동", '야외 스포츠, 레포츠 활동'),
    ("지역 문화예술 / 공연 / 전시시설 관람", '지역 문화예술 / 공연 / 전시시설 관람'),
    ("유흥 / 오락(나이트라이프)", '유흥 / 오락(나이트라이프)'),
    ("캠핑", '캠핑'),
    ("지역 축제 / 이벤트 참가", '지역 축제 / 이벤트 참가'),
    ("온천 / 스파", '온천 / 스파'),
    ("교육 / 체험 프로그램 참가", '교육 / 체험 프로그램 참가'),
    ("드라마 촬영지 방문", '드라마 촬영지 방문'),
    ("종교 / 성지 순례", '종교 / 성지 순례'),
    ("Well - ness 여행", 'Well - ness 여행'),
    ("SNS 인생샷 여행", 'SNS 인생샷 여행'),
    ("호캉스 여행", '호캉스 여행'),
    ("신규 여행지 발굴", '신규 여행지 발굴'),
    ("반려동물 동반 여행", '반려동물 동반 여행'),
    ("인플루언서 따라하기 여행", '인플루언서 따라하기 여행'),
    ("친환경 여행(플로깅 여행)", '친환경 여행(플로깅 여행)'),
    ("등반 여행", '등반 여행'),
    ("기타", '기타'),
]

# 방문지 정보
class Visit(models.Model):
    visit_name = models.CharField(max_length=100, blank=True, null=True)  # 방문지 이름 VISIT_AREA_NM
    address = models.CharField(max_length=255, blank=True, null=True) # 방문지 주소 ROAD_NM_ADDR
    photos = models.ImageField("관광지 이미지", upload_to="recommend/tour_images", blank=True, null=True) # 방문지 이미지

    class Meta:
        unique_together = ['visit_name', 'address']

    def __str__(self):
        return f"{self.visit_name}"


# 여행 기본 정보 (TN_TRAVEL)
class Travel(models.Model):
    travel_id = models.CharField(max_length=50, primary_key=True)  # 여행 ID
    traveler = models.ForeignKey(User, on_delete=models.CASCADE)  # 여행객과 연결
    travel_name = models.TextField(blank=True, null=True)
    start_date = models.DateField()  # 여행 시작일
    end_date = models.DateField()  # 여행 종료일
    movement_name = models.CharField(max_length=100, blank=True)  # 이동 수단 이름

    # 동반자 정보 (TN_COMPANION_INFO)
    companion_num = models.PositiveIntegerField(default=0)  # 동반자 수
    relationship = models.TextField(blank=True, null=True)  # 관계 (예: 가족, 친구 등)

    # 여행지 정보
    visits = models.ManyToManyField(Visit)  # 여러 방문지를 여행과 연결

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError('여행 시작일은 종료일보다 이전이어야 합니다.')

    def __str__(self):
        return f"{self.travel_name} ({self.start_date} to {self.end_date})"


# 여행 소비 정보 (TN_CONSUME_HIS)
class Consume(models.Model):
    TRAVEL_EXPENSE_CATEGORIES = [
        ('transportation', '이동수단'),
        ('lodging', '숙박'),
        ('advance', '사전 소비'),
        ('activity', '활동'),
    ]
    travel = models.ForeignKey(Travel, on_delete=models.CASCADE)  # 여행과 연결
    category = models.CharField(max_length=20, choices=TRAVEL_EXPENSE_CATEGORIES)  # 소비 카테고리
    consume_name = models.CharField(max_length=100, blank=True)  # 소비 항목 이름
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2)  # 결제 금액
    details = models.TextField(blank=True, null=True, verbose_name="세부 내용")  # 세부 내용

    def clean(self):
        if self.payment_amount < 0:
            raise ValidationError('결제 금액은 0보다 커야 합니다.')

    def __str__(self):
        return f"{self.category} - {self.consume_name} - {self.payment_amount} 원"





# 인기 여행지
class PopularTour(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)  # Visit 모델과 연결
    visit_count = models.PositiveIntegerField(default=0)  # 방문 횟수

    def __str__(self):
        return f"{self.visit.visit_name} - {self.visit.address} ({self.visit_count} visits)"


# AI 추천 여행지
class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 사용자와 연결
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE)  # 방문지와 연결
    score = models.FloatField(default=0)  # 추천 점수

    def __str__(self):
        return f"추천: {self.visit.visit_name} for {self.user.username} (점수: {self.score})"