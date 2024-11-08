from django.db import models
import json

class TouristSpot(models.Model):
    touristspot_name = models.CharField(max_length=50)              # 관광지명
    main_cate = models.CharField(max_length=50)         # 1차 카테고리
    second_cate = models.CharField(max_length=50)       # 2차 카테고리
    third_cate = models.CharField(max_length=50)        # 3차 카테고리
    description = models.TextField()                    # 관광지 설명
    tags = models.JSONField(blank=True, null=True)      # 태그 및 기타 속성 정보
    tags_text = models.TextField(blank=True, null=True) # JSON 값 텍스트 저장 필드

    def save(self, *args, **kwargs):
        # tags 필드의 값을 텍스트로 변환하여 tags_text에 저장
        self.tags_text = ', '.join([str(value) for value in self.tags.values()]) if self.tags else ''
        super().save(*args, **kwargs)

    def __str__(self):
        return self.touristspot_name