from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.core.paginator import Paginator
from recommend.models import PopularTour, Recommendation, Visit
from recommend.utils import calculate_related_spots
from accounts.models import User




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
    # user = request.user
    user = User.objects.all()[0]  # 임의로 user 지정
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

    # 방문지 정보와 관련된 다른 데이터를 context에 담아서 템플릿에 전달
    return render(request, 'recommend/tour_info.html', {
        'visit': visit,
        'visit_count':visit_count,
        'related_spots': related_spots,
    })













# def create_travel(request):
#     if request.method == 'POST':
#         form = TravelForm(request.POST)
#         if form.is_valid():
#             form.save()  # 저장
#             return redirect('success_url')  # 성공적으로 저장 후 리디렉션
#     else:
#         form = TravelForm()
#
#     return render(request, 'your_template.html', {'form': form})