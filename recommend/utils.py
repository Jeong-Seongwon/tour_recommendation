from django.core.cache import cache
from django.db.models import Count, F, Q, Value, IntegerField, FloatField, ExpressionWrapper
from .models import Visit, Travel


def calculate_related_spots(visit_id, limit=10):
    """
    주어진 방문지와 연관된 다른 방문지들을 찾고 연관성을 계산하는 함수

    Args:
        visit_id (int): 기준이 되는 방문지 ID
        limit (int): 반환할 최대 결과 수

    Returns:
        list: 연관 방문지들의 정보와 연관성 점수를 포함하는 딕셔너리 리스트
    """
    # 캐시 키 생성
    cache_key = f'related_spots_{visit_id}_{limit}'

    # 캐시에서 값 가져오기
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        # 현재 방문지 조회
        current_visit = Visit.objects.get(id=visit_id)

        # 현재 방문지가 포함된 모든 여행 조회
        related_travels = Travel.objects.filter(visits=current_visit)

        # 연관된 방문지들과 그들의 출현 빈도를 계산
        related_visits = (
            Visit.objects
            .filter(travel__in=related_travels)  # 현재 방문지와 같은 여행에 포함된 방문지들
            .exclude(id=visit_id)  # 현재 방문지는 제외
            .annotate(
                # 해당 방문지가 나타난 여행 수
                appearance_count=Count('travel', distinct=True),
                # 전체 여행 수 (현재 방문지가 포함된 여행 수)
                total_travels=Value(related_travels.count(), output_field=IntegerField())
            )
            .annotate(
                # 연관성 점수 계산: (같이 나타난 횟수) / (전체 여행 수)
                relation_score=ExpressionWrapper(
                    F('appearance_count') * 1.0 / F('total_travels'),
                    output_field=FloatField()
                )
            )
        )

        # 결과 리스트 생성
        results = []
        for related_visit in related_visits:
            results.append({
                'visit': related_visit,
                'appearance_count': related_visit.appearance_count,
                'relation_score': round(related_visit.relation_score, 4),
                'total_travels': related_visit.total_travels
            })

        # 연관성 점수로 정렬 (높은 순)
        results.sort(key=lambda x: (-x['relation_score'], -x['appearance_count']))
        results = results[:limit]

        # 결과를 캐시에 저장 (1시간)
        cache.set(cache_key, results, timeout=3600)

        return results

    except Visit.DoesNotExist:
        return []

    except Exception as e:
        print(f"Error in calculate_related_spots: {str(e)}")
        return []