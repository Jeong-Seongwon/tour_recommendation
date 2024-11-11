from django.core.cache import cache
from django.db.models import Count, F, Q, Value, IntegerField, FloatField, ExpressionWrapper, DurationField
from .models import Visit, Travel, Consume


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


def predict_travel_expenses(travel):
    """
    여행지, 기간, 이동수단, 동반자 정보 등을 고려하여 유사 여행 기반으로 예상 소비 금액을 계산합니다.

    Returns:
    - predicted_amount: 예상 소비 금액
    - prediction_details: 예측 상세 내역
    """
    from datetime import datetime
    from django.db.models import Avg, Count, Q, F, ExpressionWrapper, DecimalField
    from django.db.models.functions import ExtractMonth
    from decimal import Decimal

    # 날짜 객체로 변환
    if isinstance(travel.start_date, str):
        travel.start_date = datetime.strptime(travel.start_date, '%Y-%m-%d').date()
    if isinstance(travel.end_date, str):
        travel.end_date = datetime.strptime(travel.end_date, '%Y-%m-%d').date()

    # 여행 기간 계산
    travel_days = (travel.end_date - travel.start_date).days + 1
    travel_month = travel.start_date.month

    # 방문할 지역 목록
    visit_areas = list(travel.visits.values_list('address', flat=True))

    # 유사 여행 찾기 기본 쿼리
    similar_travels = Travel.objects.annotate(
        duration=ExpressionWrapper(
            F('travel.end_date') - F('travel.start_date'),
            output_field=DurationField()
        ),
        month=ExtractMonth('travel.start_date'),
        visit_count=Count('travel.visits')
    )

    # 1단계: 가장 엄격한 조건으로 유사 여행 찾기
    strict_conditions = similar_travels.filter(
        duration__range=(travel_days - 1, travel_days + 1),
        month__range=(travel_month - 1, travel_month + 1),
        visit_count__range=(len(travel.visits) - 1, len(travel.visits) + 1),
        visits__address__in=visit_areas,
        companion_num__range=(max(0, travel.companion_num - 1), travel.companion_num + 1)
    )

    if travel.movement_name:
        strict_conditions = strict_conditions.filter(movement_name=travel.movement_name)
    if travel.relationship:
        strict_conditions = strict_conditions.filter(relationship=travel.relationship)

    strict_conditions = strict_conditions.distinct()

    # 2단계: 조건을 점진적으로 완화하며 충분한 데이터 확보
    if strict_conditions.count() < 3:
        relaxed_conditions = similar_travels.filter(
            duration__range=(travel_days - 2, travel_days + 2),
            month__range=(travel_month - 2, travel_month + 2),
            visit_count__range=(len(travel.visits) - 2, len(travel.visits) + 2),
            visits__address__in=visit_areas
        )

        if travel.movement_name:
            relaxed_conditions = relaxed_conditions.filter(
                Q(movement_name=travel.movement_name) |
                Q(movement_name__isnull=True)
            )

        relaxed_conditions = relaxed_conditions.distinct()

        # 사용할 유사 여행 데이터 선택
        similar_travels = relaxed_conditions if relaxed_conditions.count() >= 3 else strict_conditions
    else:
        similar_travels = strict_conditions

    # 인원수에 따른 비용 조정 계수 계산
    def calculate_person_coefficient(target_num, reference_num):
        if reference_num == 0 or target_num == 0:
            return 1
        # 1인당 비용은 인원수가 늘어날수록 감소 (규모의 경제)
        return (target_num / reference_num) * 0.8 + 0.2

    # 카테고리별 평균 비용 계산 및 조정
    expense_details = {}
    if similar_travels.exists():
        for category, _ in Consume.TRAVEL_EXPENSE_CATEGORIES:
            # 유사 여행들의 해당 카테고리 평균 비용 계산
            similar_expenses = Consume.objects.filter(
                travel__in=similar_travels,
                category=category
            ).annotate(
                cost_per_person=ExpressionWrapper(
                    F('payment_amount') / (F('travel__companion_num') + 1),
                    output_field=DecimalField()
                )
            ).aggregate(
                avg_amount=Avg('payment_amount'),
                avg_cost_per_person=Avg('cost_per_person')
            )

            avg_amount = similar_expenses['avg_amount'] or 0
            avg_cost_per_person = similar_expenses['avg_cost_per_person'] or 0

            # 기준 여행의 평균 동반자 수
            avg_companion_num = similar_travels.aggregate(
                avg_companions=Avg('companion_num')
            )['avg_companions'] or 0

            # 인원수 차이에 따른 비용 조정
            person_coefficient = calculate_person_coefficient(
                travel.companion_num + 1,  # +1 for the traveler
                avg_companion_num + 1
            )

            # 카테고리별 특성에 따른 비용 조정
            if category == 'lodging':
                # 숙박비는 인원수에 덜 민감
                adjusted_amount = avg_amount * (0.7 + 0.3 * person_coefficient)
            elif category == 'transportation':
                # 교통비는 이동수단에 따라 조정
                transport_coefficient = 1.0
                if travel.movement_name != similar_travels.first().travel.movement_name:
                    if travel.movement_name == '자가용':
                        transport_coefficient = 0.8  # 대중교통 대비 자가용 비용 감소
                    elif travel.movement_name == '대중교통':
                        transport_coefficient = 1.2  # 자가용 대비 대중교통 비용 증가
                adjusted_amount = avg_amount * person_coefficient * transport_coefficient
            else:
                # 기타 비용은 인원수에 비례
                adjusted_amount = avg_amount * person_coefficient

            # 여행 기간에 따른 조정
            if category in ['lodging', 'transportation', 'activity']:
                reference_duration = similar_travels.first().duration.days
                adjusted_amount = (adjusted_amount / reference_duration) * travel_days

            expense_details[category] = round(adjusted_amount, 0)
    else:
        # 유사 여행이 없을 경우 기본값에 인원수 반영
        base_costs = {
            'transportation': 50000 * travel_days,
            'lodging': 100000 * (travel_days - 1),
            'activity': 30000 * len(travel.visits),
            'advance': 20000 * travel_days
        }
        person_coefficient = calculate_person_coefficient(travel.companion_num + 1, 2)  # 기본값은 2인 여행 기준
        expense_details = {
            category: round(amount * person_coefficient, 0)
            for category, amount in base_costs.items()
        }

    # 총 예상 비용 계산
    predicted_amount = sum(expense_details.values())

    # 신뢰도 점수 계산 (다양한 요소 고려)
    base_confidence = min(similar_travels.count() * 20, 100)
    movement_match = 1 if travel.movement_name and similar_travels.filter(
        movement_name=travel.movement_name).exists() else 0.8
    travel.relationship_match = 1 if travel.relationship and similar_travels.filter(
        relationship=travel.relationship).exists() else 0.8

    confidence_score = base_confidence * movement_match * travel.relationship_match

    # 예측 상세 정보
    prediction_details = {
        'expense_details': expense_details,
        'similar_travels_count': similar_travels.count(),
        'confidence_score': round(confidence_score, 1),
        'travel_days': travel_days,
        'visit_count': len(travel.visits),
        'companion_info': {
            'number': travel.companion_num,
            'travel.relationship': travel.relationship
        },
        'movement_name': travel.movement_name,
        'similar_travels_characteristics': {
            'avg_companion_num': float(similar_travels.aggregate(
                Avg('companion_num'))['companion_num__avg'] or 0),
            'common_movement': similar_travels.values('movement_name').annotate(
                count=Count('id')).order_by('-count').first()
        }
    }

    return int(predicted_amount), prediction_details