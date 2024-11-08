from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Sum, Count, F, Value, DecimalField, ExpressionWrapper, DurationField
from django.db.models.functions import Coalesce
from collections import Counter
from recommend.models import Travel, Consume, Visit


def chart_view(request):
    return render(request, "chart/chart.html")


def travel_statistics(request):
    try:
        # 여행 목적 별 통계
        travel_names = Travel.objects.values_list('travel_name', flat=True)
        travel_purpose_counts = Counter()
        for name in travel_names:
            purposes = name.split(',')
            for purpose in purposes:
                travel_purpose_counts[purpose.strip()] += 1
    except Exception:
        travel_purpose_counts = Counter()  # 예외 발생 시 빈 Counter

    try:
        # 여행 기간별 카운트 계산
        travel_durations = Travel.objects.annotate(
            duration_days=ExpressionWrapper(
                F('end_date') - F('start_date'),
                output_field=DurationField()
            )
        ).values_list('duration_days', flat=True)
        travel_durations = [duration.days for duration in travel_durations if duration]
        duration_counts = Counter(travel_durations)
    except Exception:
        duration_counts = {}

    try:
        # 이동 수단 차트
        movement_counts = Travel.objects.values('movement_name').annotate(count=Count('movement_name'))
        movement_counts = list(movement_counts) if movement_counts else []
    except Exception:
        movement_counts = []

    try:
        # 동반자 수 차트
        companion_counts = Travel.objects.values('companion_num').annotate(count=Count('companion_num')).order_by('companion_num')
        companion_counts = list(companion_counts) if companion_counts else []
    except Exception:
        companion_counts = []

    try:
        # 소비 카테고리별 금액 차트
        expense_counts = Consume.objects.values('category').annotate(total_amount=Sum('payment_amount'))
        expense_counts = list(expense_counts) if expense_counts else []
    except Exception:
        expense_counts = []

    try:
        # 시, 군, 구 별 여행 수 차트
        visit_addresses = Visit.objects.values_list('address', flat=True)
        city_counts = Counter()
        city_expenses = Counter()
        for address in visit_addresses:
            if address:
                parts = address.split()
                city = ''
                if len(parts) > 1 and (parts[1].endswith('시') or parts[1].endswith('군') or parts[1].endswith('구')):
                    city = f"{parts[0]} {parts[1]}"
                else:
                    city = parts[0]
                city_counts[city] += 1

        # 도시별 평균 소비 금액 계산
        for city in city_counts.keys():
            average_spending = Visit.objects.filter(address__icontains=city).aggregate(
                average_spending=Coalesce(
                    Avg('travel__consume__payment_amount', output_field=DecimalField()),
                    Value(0, output_field=DecimalField())
                )
            )['average_spending'] or 0
            city_expenses[city] = average_spending
    except Exception:
        city_counts = Counter()
        city_expenses = Counter()

    context = {
        'travel_purpose_counts': dict(travel_purpose_counts),
        'duration_counts': dict(duration_counts),
        'movement_counts': movement_counts,
        'companion_counts': companion_counts,
        'expense_counts': expense_counts,
        'city_counts': dict(city_counts),
        'visit_expense': dict(city_expenses),
    }

    return JsonResponse(context)
