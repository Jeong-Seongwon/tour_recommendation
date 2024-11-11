from lib2to3.fixes.fix_input import context

from django.contrib.auth.decorators import login_required
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


@login_required
def user_travel_statistics(request):
    user = request.user

    # 여행 목적 별 통계
    try:
        user_travel_names = Travel.objects.filter(traveler=user).values_list('travel_name', flat=True)
        user_travel_purpose_counts = Counter()
        for name in user_travel_names:
            purposes = name.split(',')
            for purpose in purposes:
                user_travel_purpose_counts[purpose.strip()] += 1
    except Exception:
        user_travel_purpose_counts = Counter()

    # 여행 기간별 카운트 계산
    try:
        user_travel_durations = Travel.objects.filter(traveler=user).annotate(
            duration_days=ExpressionWrapper(
                F('end_date') - F('start_date'),
                output_field=DurationField()
            )
        ).values_list('duration_days', flat=True)
        user_travel_durations = [duration.days for duration in user_travel_durations if duration]
        user_duration_counts = Counter(user_travel_durations)
    except Exception:
        user_duration_counts = {}

    # 이동 수단 차트
    try:
        user_movement_counts = Travel.objects.filter(traveler=user).values('movement_name').annotate(count=Count('movement_name'))
        user_movement_counts = list(user_movement_counts) if user_movement_counts else []
    except Exception:
        user_movement_counts = []

    # 동반자 수 차트
    try:
        user_companion_counts = Travel.objects.filter(traveler=user).values('companion_num').annotate(count=Count('companion_num')).order_by('companion_num')
        user_companion_counts = list(user_companion_counts) if user_companion_counts else []
    except Exception:
        user_companion_counts = []

    # 소비 카테고리별 금액 차트
    try:
        user_expense_counts = Consume.objects.filter(travel__traveler=user).values('category').annotate(total_amount=Sum('payment_amount'))
        user_expense_counts = list(user_expense_counts) if user_expense_counts else []
    except Exception:
        user_expense_counts = []

    # 시, 군, 구 별 여행 수 차트
    try:
        user_travel_visits = Travel.objects.filter(traveler=user).values_list('visits', flat=True)
        user_visit_addresses = Visit.objects.filter(id__in=user_travel_visits).values_list('address', flat=True)
        user_city_counts = Counter()
        user_city_expenses = Counter()

        for address in user_visit_addresses:
            if address:
                parts = address.split()
                if len(parts) > 1 and (parts[1].endswith('시') or parts[1].endswith('군') or parts[1].endswith('구')):
                    city = f"{parts[0]} {parts[1]}"
                else:
                    city = parts[0]
                user_city_counts[city] += 1

        # 도시별 평균 소비 금액 계산
        for city in user_city_counts.keys():
            average_spending = Visit.objects.filter(address__icontains=city, travel__traveler=user).aggregate(
                average_spending=Coalesce(
                    Avg('travel__consume__payment_amount', output_field=DecimalField()),
                    Value(0, output_field=DecimalField())
                )
            )['average_spending'] or 0
            user_city_expenses[city] = average_spending
    except Exception:
        user_city_counts = Counter()
        user_city_expenses = Counter()

    context = {
        'user_travel_purpose_counts': dict(user_travel_purpose_counts),
        'user_duration_counts': dict(user_duration_counts),
        'user_movement_counts': user_movement_counts,
        'user_companion_counts': user_companion_counts,
        'user_expense_counts': user_expense_counts,
        'user_city_counts': dict(user_city_counts),
        'user_visit_expense': dict(user_city_expenses),
    }

    return JsonResponse(context)