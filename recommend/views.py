from lib2to3.fixes.fix_input import context

from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.core.paginator import Paginator
from recommend.models import PopularTour, Recommendation, Visit, Travel, Consume, TRAVEL_PURPOSE_CHOICES
from recommend.utils import calculate_related_spots, predict_travel_expenses
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from recommend.forms import TravelForm




def tour_view(request):
    return render(request, "recommend/tours.html")


def pop_tours_view(request):
    page = int(request.GET.get('page', 1))
    items_per_page = 20

    # 모든 투어를 방문 횟수로 정렬
    all_tours = PopularTour.objects.order_by('-visit_count')

    # 페이지네이터 생성
    paginator = Paginator(all_tours, items_per_page)

    try:
        tours = paginator.page(page)
        has_next = tours.has_next()

        context = {
            'tours': tours,
            'has_next': has_next
        }

        tours_html = render_to_string('recommend/tours_list.html', context)

        return JsonResponse({
            'tours_html': tours_html,
            'has_next': has_next,
            'next_page': page + 1 if has_next else None
        })
    except Exception as e:
        print(f"Error in pop_tours_view: {e}")
        return JsonResponse({
            'tours_html': '',
            'has_next': False,
            'next_page': None
        })



def customer_view(request):
    return render(request, "recommend/customers.html")


def recommend_tours_view(request):
    page = int(request.GET.get('page', 1))
    items_per_page = 20

    # 로그인된 사용자
    user = request.user
    # user = User.objects.first()  # 임의로 user 지정
    username = user.username

    # 특정 사용자의 AI 추천 여행지를 score 순으로 정렬
    all_recommendations = (
        Recommendation.objects.filter(user_id=username)
        .select_related('visit')
        .order_by('-score')
    )

    # 페이지네이터 생성
    paginator = Paginator(all_recommendations, items_per_page)

    try:
        recommendations = paginator.page(page)
        has_next = recommendations.has_next()

        # 추천 리스트에 visit_count 추가
        recommendations_with_count = []
        for rec in recommendations:
            # visit와 관련된 PopularTour 인스턴스가 존재하는지 확인하고 visit_count를 가져옴
            try:
                visit_count = PopularTour.objects.get(visit=rec.visit).visit_count
            except PopularTour.DoesNotExist:
                visit_count = 0

            recommendations_with_count.append({
                'recommendation': rec,
                'visit_count': visit_count
            })

        # context에 추천 항목과 방문 횟수를 포함하여 템플릿으로 전달
        context = {
            'recommendations_with_count': recommendations_with_count,
            'has_next': has_next
        }

        # 템플릿 렌더링
        customers_html = render_to_string('recommend/customers_list.html', context)

        return JsonResponse({
            'customers_html': customers_html,
            'has_next': has_next,
            'next_page': page + 1 if has_next else None
        })
    except Exception as e:
        print(f"Error in recommend_tours_view: {e}")
        return JsonResponse({
            'customers_html': '',
            'has_next': False,
            'next_page': None
        })


def tour_info_view(request, id):
    # Visit 객체를 ID로 검색, 없으면 404 에러 페이지로 이동
    visit = get_object_or_404(Visit, id=id)

    try:
        visit_count = PopularTour.objects.get(visit=visit).visit_count
    except PopularTour.DoesNotExist:
        visit_count = 0

    # 연관된 방문지 가져오기
    related_spots = calculate_related_spots(id, limit=10)

    # 여행 방문 예정지 목록
    planned_visits = request.session.get('planned_visits', [])

    # 방문지 정보와 관련된 다른 데이터를 context에 담아서 템플릿에 전달
    return render(request, 'recommend/tour_info.html', {
        'visit': visit,
        'visit_count':visit_count,
        'related_spots': related_spots,
        'planned_visits': planned_visits,
    })


# 방문 예정지 목록 페이지
@login_required
def planned_visits(request):
    planned_visit_ids = request.session.get('planned_visits', [])
    planned_visits = Visit.objects.filter(id__in=planned_visit_ids)

    form = TravelForm()  # 날짜 입력 폼 포함

    context = {
        'form': form,
        'planned_visits': planned_visits,
        'TRAVEL_PURPOSE_CHOICES': TRAVEL_PURPOSE_CHOICES,
    }
    return render(request, 'recommend/travel_plan.html', context)


# 방문 예정지 추가
@login_required
def add_to_planned_visits(request, visit_id):
    planned_visits = request.session.get('planned_visits', [])

    if visit_id not in planned_visits:  # 중복 추가 방지
        planned_visits.append(visit_id)
        request.session['planned_visits'] = planned_visits

    # 이전 페이지로 리다이렉트
    return redirect(request.META.get('HTTP_REFERER', '/'))


# 방문 예정지 삭제
@login_required
def remove_from_planned_visits(request, visit_id):
    planned_visits = request.session.get('planned_visits', [])

    if visit_id in planned_visits:
        planned_visits.remove(visit_id)
        request.session['planned_visits'] = planned_visits

    # 이전 페이지로 리다이렉트
    return redirect(request.META.get('HTTP_REFERER', '/'))


# 방문 예정지를 기반으로 여행 생성
@login_required
def create_travel_from_planned_visits(request):
    if request.method == 'POST':
        planned_visits_ids = request.session.get('planned_visits', [])
        visits = Visit.objects.filter(id__in=planned_visits_ids)

        form = TravelForm(request.POST)
        if form.is_valid():
            travel = form.save(commit=False)
            travel.traveler = request.user  # 로그인된 사용자 설정
            travel.save()
            travel.visits.set(visits)  # 방문지 설정

            request.session['planned_visits'] = []  # 세션 초기화
            return redirect('recommend:travel_detail', travel_id=travel.travel_id)
        else:
            # 폼 유효성 검증 실패 시 원래 페이지로 돌아가고 입력값을 그대로 두기
            planned_visits = Visit.objects.filter(id__in=planned_visits_ids)  # 계획된 방문지 재조회
            context = {
                'form': form,
                'planned_visits': planned_visits,
                'TRAVEL_PURPOSE_CHOICES': TRAVEL_PURPOSE_CHOICES,
            }
            return render(request, 'recommend/travel_plan.html', context)

    return redirect('recommend:planned_visits')


# 여행 상세 페이지
@login_required
def travel_detail(request, travel_id=None):
    user = request.user
    user_travels = Travel.objects.filter(traveler=user)

    # travel_id가 None이면 사용자의 마지막 여행을 가져옴
    if travel_id is None:
        travel = user_travels.order_by('-travel_id').first()  # 마지막 여행
    else:
        travel = get_object_or_404(Travel, travel_id=travel_id)

    # 여행 이름을 쉼표로 분리하여 리스트로 만듬
    travel_names = [name.strip() for name in travel.travel_name.split(',')]

    # 소비 정보 가져오기
    consumes = Consume.objects.filter(travel=travel)

    # 예산 예측 관련 변수 초기화
    predicted_amount = 0
    prediction_details = None

    # 소비가 있을 경우 총 금액 계산
    total_amount = sum(consume.payment_amount for consume in consumes)

    # 카테고리별 소비 금액 계산
    category_expenses = {}
    if consumes:
        for consume in consumes:
            category = consume.category
            category_expenses[category] = category_expenses.get(category, 0) + consume.payment_amount
    else:
        # 소비 정보가 없으면 예산 예측
        predicted_amount, prediction_details = predict_travel_expenses(travel)

    context = {
        'user_travels': user_travels,
        'travel': travel,
        'travel_names': travel_names,
        'consumes': consumes,
        'total_amount': total_amount,
        'category_expenses': category_expenses,
        'predicted_amount': predicted_amount,
        'prediction_details': prediction_details,
    }
    return render(request, 'recommend/travel_detail.html', context)