# views.py
from django.contrib.postgres.search import TrigramSimilarity
from django.http import JsonResponse
from rest_framework.decorators import api_view
from .models import TouristSpot
import json
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render


@csrf_exempt
def chatbot(request):
    initial_message = None
    initial_response = None

    if request.method == 'POST':
        user_input = request.POST.get('user-input')
        if user_input:
            # 초기 검색 수행
            results = perform_search(user_input)
            if results:
                initial_message = user_input
                initial_response = format_response(results)

    return render(request, 'chatbot/chatbot.html', {
        'initial_message': initial_message,
        'initial_response': initial_response
    })


@api_view(['POST'])
def search_tourist_spot(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        search_query = data.get("query")

        if not search_query:
            return JsonResponse({"error": "No query provided."}, status=400)

        results = perform_search(search_query)

        if results:
            response_data = format_response(results)
            return JsonResponse(response_data, status=200)
        else:
            return JsonResponse({"message": "No similar tourist spot found."}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def perform_search(query):
    return (
        TouristSpot.objects
        .annotate(
            similarity=(
                    TrigramSimilarity('touristspot_name', query) * 2.0 +  # 이름 매칭에 더 높은 가중치
                    TrigramSimilarity('main_cate', query) * 1.5 +
                    TrigramSimilarity('second_cate', query) * 1.5 +
                    TrigramSimilarity('third_cate', query) * 1.5 +
                    TrigramSimilarity('description', query) +
                    TrigramSimilarity('tags_text', query) * 1.2
            )
        )
        .filter(similarity__gt=0.1)
        .order_by('-similarity')
        .first()
    )


def format_response(result):
    return {
        "touristspot_name": result.touristspot_name,
        "main_category": result.main_cate,
        "second_category": result.second_cate,
        "third_category": result.third_cate,
        "description": result.description,
        "tags": result.tags
    }