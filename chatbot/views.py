from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import ExpressionWrapper, FloatField, Value, CharField
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .models import TouristSpot
import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.core.serializers.json import DjangoJSONEncoder
# from konlpy.tag import Okt



@csrf_exempt
def chatbot(request):
    initial_message = None
    initial_response = None

    if request.method == 'POST':
        user_input = request.POST.get('user-input')  # 폼 데이터를 사용할 경우

        response_data = search_logic(user_input)
        # print(response_data)

        if response_data:
            initial_message = user_input
            # JSON으로 직렬화하여 템플릿에 전달
            initial_response = json.dumps(response_data, cls=DjangoJSONEncoder)

    return render(request, 'chatbot/chatbot.html', {
        'initial_message': initial_message,
        'initial_response': initial_response
    })


@api_view(['POST'])
def search_tourist_spot(request):
    try:
        data = request.data
        search_query = data.get("query")

        if not search_query:
            return JsonResponse({"error": "No query provided."}, status=400)

        response_data = search_logic(search_query)
        print(response_data)

        if response_data:
            return JsonResponse(response_data)
        else:
            return JsonResponse({"message": "관광지를 찾을 수 없습니다."}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    except Exception as e:
        print(f"Error: {str(e)}")  # 디버깅을 위한 로그
        return JsonResponse({"error": "서버 오류가 발생했습니다."}, status=500)




def identify_field_query(query):
    # 필드별 키워드 매핑
    field_keywords = {
        'main_cate': ['주 카테고리', '메인 카테고리', '1차 카테고리', '대분류'],
        'second_cate': ['세부 카테고리', '2차 카테고리', '중분류'],
        'third_cate': ['3차 카테고리', '소분류'],
        'tags': ['태그', '특징', '속성', '정보', '소개', '설명', '안내'],
    }
    tags_field_keywords = {
        '날짜': ['날짜', '연도', '년'],
        '링크': ['링크', '웹사이트'],
        '사건': ['사건', '이벤트'],
        '사람': ['사람', '인물'],
        '주소': ['주소'],
        '지역': ['지역'],
        '인공물': ['인공물', '유물'],
        '부대정보': ['부대정보', '주차', '시설'],
        '기타사항': ['기타사항'],
        '전화번호': ['전화번호'],
        '문명': ['문명'],
        '기관': ['기관'],
        '시간': ['시간'],
    }

    for field, keywords in field_keywords.items():
        # 쿼리에서 키워드가 포함된 필드 찾기
        if any(keyword in query for keyword in keywords):
            return field

    for field, keywords in tags_field_keywords.items():
        if any(keyword in query for keyword in keywords):
            return field

    return None  # 필드를 찾을 수 없으면 None 반환


# # 형태소 분석기를 사용하여 명사만 추출
# def extract_nouns(text):
#     okt = Okt()
#     # 텍스트에서 명사만 추출
#     nouns = okt.nouns(text)
#     return nouns


def search_logic(query):
    all_spots = TouristSpot.objects.all()
    spots = [spot for spot in all_spots if spot.touristspot_name in query]

    # query_nouns = extract_nouns(query)
    #
    # for noun in query_nouns:
    #     spot = all_spots.annotate(
    #         similarity=TrigramSimilarity('touristspot_name', noun)
    #     ).filter(similarity__gt=0.1)
    #
    #     if spot.exists():
    #         break  # 첫 번째 일치하는 결과만 찾기

    if spots:
        spot = spots[0]
        # 관광지 이름이 포함된 경우
        requested_field = identify_field_query(query)

        if requested_field:
            # 특정 필드에 대한 질문인 경우
            return format_field_response(spot, requested_field)
        else:
            # 일반적인 상세 정보 요청
            return format_detailed_response(spot)
    else:
        # 관광지 이름이 없는 경우 연관된 관광지 목록 반환
        similar_spots = (
            TouristSpot.objects
            .annotate(
                similarity=ExpressionWrapper(
                        Coalesce(TrigramSimilarity('touristspot_name', query), 0) * 2.0 +
                        Coalesce(TrigramSimilarity('main_cate', query), 0) * 1.5 +
                        Coalesce(TrigramSimilarity('second_cate', query), 0) * 1.5 +
                        Coalesce(TrigramSimilarity('third_cate', query), 0) * 1.5 +
                        Coalesce(TrigramSimilarity('description', query), 0) +
                        Coalesce(TrigramSimilarity('tags_text', query), 0) * 1.2,
                        output_field=FloatField()
                )
            )
            .filter(similarity__gt=0.1)
            .distinct()  # 중복제거
            .order_by('-similarity')[:10]
        )

        if similar_spots:
            return format_suggestion_response(similar_spots)
        return None


def format_field_response(result, field):
    field_names = {
        'main_cate': '주 카테고리',
        'second_cate': '세부 카테고리',
        'third_cate': '3차 카테고리',
        'description': '설명',
        'tags': '속성'
    }

    if field == 'tags':
        field_value = result.tags
    elif field in result.tags:
        field_value = result.tags.get(field, '정보 없음')
    else:
        field_value = getattr(result, field)

    return {
        "response_type": "field",
        "data": {
            "touristspot_name": result.touristspot_name,
            "field_name": field_names.get(field, field),  # 기본 필드명이 없으면 그대로 사용
            "field_value": field_value
        }
    }


def format_detailed_response(result):
    return {
        "response_type": "detail",
        "data": {
            "touristspot_name": result.touristspot_name,
            "main_category": result.main_cate,
            "second_category": result.second_cate,
            "third_category": result.third_cate,
            "description": result.description,
            "tags": result.tags
        }
    }


def format_suggestion_response(results):
    suggestions = [
        {
            "touristspot_name": spot.touristspot_name,
            "main_category": spot.main_cate,
            "second_category": spot.second_cate
        }
        for spot in results
    ]

    return {
        "response_type": "suggestions",
        "data": suggestions,
        "message": "다음 관광지들을 찾아보세요:"
    }